"""
Setup Helper - dodatkowy skrypt pomocniczy dla instalatora
Uruchamiany podczas instalacji, aby zapewnić poprawną konfigurację
"""
import os
import sys
import subprocess
from pathlib import Path
import sqlite3


def ensure_python_in_path():
    """Sprawdza czy Python jest w PATH"""
    try:
        result = subprocess.run(
            ["python", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ Python dostępny: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Python nie jest dostępny w PATH!")
        print("   Zainstaluj Pythona i zaznacz opcję 'Add Python to PATH'")
        return False


def check_disk_space():
    """Sprawdza dostępne miejsce na dysku"""
    try:
        import shutil
        stats = shutil.disk_usage(Path.cwd())
        free_gb = stats.free / (1024**3)
        
        if free_gb < 1:
            print(f"⚠ Uwaga: Mało miejsca na dysku ({free_gb:.1f} GB)")
            print("   Instalacja wymaga około 500 MB")
            return False
        
        print(f"✓ Wolne miejsce na dysku: {free_gb:.1f} GB")
        return True
    except Exception as e:
        print(f"⚠ Nie można sprawdzić miejsca na dysku: {e}")
        return True


def create_desktop_shortcut():
    """Tworzy skrót na pulpicie (opcjonalnie)"""
    try:
        # To będzie obsługiwane przez Inno Setup
        pass
    except Exception as e:
        print(f"⚠ Nie można utworzyć skrótu: {e}")


def main():
    """Główna funkcja pomocnicza"""
    print("=" * 60)
    print("  Setup Helper - Weryfikacja systemu")
    print("=" * 60)
    print()
    
    # Sprawdzenia
    python_ok = ensure_python_in_path()
    space_ok = check_disk_space()
    
    print()
    print("=" * 60)
    
    if python_ok and space_ok:
        print("✅ System gotowy do instalacji!")
        return 0
    else:
        print("⚠ Wykryto potencjalne problemy")
        return 1



def remove_buchy_column_from_habit_db(app_root: Path | None = None) -> int:
    """Remove the private 'buchy' column from habit_columns if present.

    This function will look for a file named 'habit_tracker.db' under the
    installed application tree (searching recursively from app_root or cwd),
    and perform a safe migration that recreates the table without the
    'buchy' column while preserving existing data for other columns.

    Returns 0 on success or when no action was needed; non-zero on error.
    """
    try:
        start = Path(app_root) if app_root else Path.cwd()
        db_path = None
        for p in start.rglob('habit_tracker.db'):
            db_path = p
            break

        if db_path is None:
            print("No habit_tracker.db found under", start)
            return 0

        print("Found habit DB:", db_path)

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(habit_columns)")
        cols = [row[1] for row in cur.fetchall()]
        if 'buchy' not in cols:
            print("Column 'buchy' not present; nothing to do.")
            conn.close()
            return 0

        print("Detected 'buchy' column — migrating habit_columns to remove it...")

        # Define the desired final schema columns (without 'buchy')
        final_cols = [
            'id', 'user_id', 'name', 'type', 'position', 'scale_max',
            'created_at', 'updated_at', 'deleted_at', 'synced_at',
            'version', 'is_synced', 'remote_id'
        ]

        cols_to_copy = [c for c in final_cols if c in cols]

        # Create new table with canonical schema
        cur.execute("""
            CREATE TABLE IF NOT EXISTS habit_columns_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                position INTEGER NOT NULL,
                scale_max INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER DEFAULT 1,
                is_synced BOOLEAN DEFAULT 0,
                remote_id TEXT UNIQUE,
                UNIQUE(user_id, name)
            )
        """)

        if cols_to_copy:
            sel = ",".join(cols_to_copy)
            ins = ",".join(cols_to_copy)
            cur.execute(f"INSERT INTO habit_columns_new ({ins}) SELECT {sel} FROM habit_columns")

        cur.execute("DROP TABLE habit_columns")
        cur.execute("ALTER TABLE habit_columns_new RENAME TO habit_columns")

        # Recreate indexes/triggers relied upon by the app
        cur.execute("CREATE INDEX IF NOT EXISTS idx_habit_columns_user ON habit_columns(user_id, deleted_at, position)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_habit_columns_remote ON habit_columns(remote_id)")

        conn.commit()
        conn.close()

        print("Migration completed: 'buchy' removed (if it existed)")
        return 0
    except Exception as e:
        print("Error while migrating habit DB:", e)
        return 2


if __name__ == "__main__":
    # Support a CLI flag so the installer can call this script to run the migration
    if '--run-migration' in sys.argv:
        rc = remove_buchy_column_from_habit_db()
        sys.exit(rc)
    else:
        sys.exit(main())
