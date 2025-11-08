import sqlite3
from pathlib import Path

# Połącz z bazą danych asystenta (w katalogu data projektu)
base_dir = Path(__file__).resolve().parent
db_path = base_dir / "data" / "assistant.db"

print(f"Sprawdzam bazę danych: {db_path}")
print(f"Czy istnieje: {db_path.exists()}")

if not db_path.exists():
    print("\n❌ Baza danych nie istnieje!")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Sprawdź frazy Pomodoro
cursor.execute("SELECT module, action, phrase_text, language, priority FROM assistant_phrases WHERE module = 'pomodoro' ORDER BY action, language, priority DESC")
phrases = cursor.fetchall()

print(f"\nZnaleziono {len(phrases)} fraz Pomodoro:")
for module, action, phrase, lang, priority in phrases:
    print(f"  {action:10} [{lang}] (p={priority}): {phrase}")

# Sprawdź wszystkie moduły
cursor.execute("SELECT DISTINCT module FROM assistant_phrases ORDER BY module")
modules = cursor.fetchall()
print(f"\n\nDostępne moduły ({len(modules)}):")
for (mod,) in modules:
    cursor.execute("SELECT COUNT(*) FROM assistant_phrases WHERE module = ?", (mod,))
    count = cursor.fetchone()[0]
    print(f"  {mod}: {count} fraz")

conn.close()
