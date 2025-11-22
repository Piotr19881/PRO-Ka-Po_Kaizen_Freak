# Quick IMAP connection tester for accounts in data/email_accounts.db
# Safe: prints account metadata and connection result, but never prints passwords.

import sqlite3
import keyring
import imaplib
import ssl
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DB_PATH = APP_DIR / 'data' / 'email_accounts.db'
SERVICE = 'PRO-Ka-Po_EmailAccounts'

print(f"Using DB: {DB_PATH}")
if not DB_PATH.exists():
    print("ERROR: email_accounts.db not found")
    raise SystemExit(2)

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("SELECT id, account_name, email_address, server_address, server_port, username, password_key, use_ssl, use_tls, is_active FROM email_accounts")
rows = cursor.fetchall()
if not rows:
    print("No email accounts found in DB.")
    raise SystemExit(0)

for r in rows:
    (acc_id, acct_name, email_addr, server_addr, server_port, username, pass_key, use_ssl, use_tls, is_active) = r
    print('\n' + '='*60)
    print(f"Account: {acct_name} <{email_addr}>")
    print(f"Server: {server_addr}:{server_port}  SSL={bool(use_ssl)} TLS={bool(use_tls)} Active={bool(is_active)}")

    pw = None
    try:
        pw = keyring.get_password(SERVICE, pass_key)
    except Exception as e:
        print(f"WARN: keyring failed to retrieve password for key {pass_key}: {e}")

    if pw is None:
        print("Password not found in keyring — cannot test login")
        continue

    # Try connecting
    try:
        if bool(use_ssl):
            print("Attempting IMAP SSL connection...")
            imap = imaplib.IMAP4_SSL(host=server_addr, port=int(server_port), timeout=10)
        else:
            print("Attempting IMAP (plain) connection...")
            imap = imaplib.IMAP4(host=server_addr, port=int(server_port), timeout=10)
            if bool(use_tls):
                print("Upgrading to TLS (STARTTLS)")
                imap.starttls()

        print("Logging in as:", username)
        typ, data = imap.login(username, pw)
        print("LOGIN OK:", typ)
        try:
            imap.logout()
        except Exception:
            pass
    except imaplib.IMAP4.error as e:
        print(f"IMAP AUTH/PROTOCOL ERROR: {e}")
    except ssl.SSLError as e:
        print(f"SSL ERROR: {e}")
    except Exception as e:
        print(f"Connection error: {e}")

print('\nDone.')
