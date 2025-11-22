import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'email_accounts.db')
DB_PATH = os.path.abspath(DB_PATH)

print('DB path:', DB_PATH)
if not os.path.exists(DB_PATH):
    print('ERROR: DB not found at', DB_PATH)
    raise SystemExit(1)

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
# Find tables and update username from the appropriate email column
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
updated_any = False
for t in tables:
    cols_info = cur.execute(f"PRAGMA table_info('{t}')").fetchall()
    cols = [c[1] for c in cols_info]
    # look for either 'email' or 'email_address'
    email_col = None
    if 'email' in cols:
        email_col = 'email'
    elif 'email_address' in cols:
        email_col = 'email_address'

    if email_col and 'username' in cols:
        print(f"\nFound candidate table: {t} (email column: {email_col})")
        rows = cur.execute(f"SELECT id, {email_col}, username FROM {t}").fetchall()
        print('Before:')
        for r in rows:
            print(r)

        # Build and execute update statement safely
        update_sql = f"UPDATE {t} SET username = {email_col} WHERE username IS NULL OR username = '' OR username <> {email_col}"
        cur.execute(update_sql)
        con.commit()
        updated_any = True

        rows2 = cur.execute(f"SELECT id, {email_col}, username FROM {t}").fetchall()
        print('After:')
        for r in rows2:
            print(r)

if not updated_any:
    print('No matching table with both an email column and username column found. No changes made.')

con.close()
print('\nDone')
