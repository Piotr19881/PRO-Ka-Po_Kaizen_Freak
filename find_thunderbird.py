import os
import re

# Typowe lokalizacje profili Thunderbird
thunderbird_paths = [
    os.path.expandvars(r"%APPDATA%\Thunderbird\Profiles"),
    os.path.expandvars(r"%LOCALAPPDATA%\Thunderbird\Profiles"),
]

print("Szukam profili Thunderbird...")
for base_path in thunderbird_paths:
    if os.path.exists(base_path):
        print(f"\n✓ Znaleziono: {base_path}")
        
        # Lista profili
        for profile in os.listdir(base_path):
            profile_path = os.path.join(base_path, profile)
            if os.path.isdir(profile_path):
                print(f"\n  Profil: {profile}")
                
                # Szukaj folderów Mail i ImapMail
                mail_path = os.path.join(profile_path, "Mail")
                imap_path = os.path.join(profile_path, "ImapMail")
                
                for mail_type, mail_dir in [("Mail", mail_path), ("ImapMail", imap_path)]:
                    if os.path.exists(mail_dir):
                        print(f"\n    📁 {mail_type}: {mail_dir}")
                        
                        # Lista kont email
                        for account in os.listdir(mail_dir):
                            account_path = os.path.join(mail_dir, account)
                            if os.path.isdir(account_path):
                                print(f"\n      Konto: {account}")
                                
                                # Szukaj folderu "rozmowy"
                                for item in os.listdir(account_path):
                                    item_path = os.path.join(account_path, item)
                                    if 'rozmow' in item.lower():
                                        print(f"        🎯 ZNALEZIONO: {item}")
                                        print(f"           Pełna ścieżka: {item_path}")
                                        
                                        # Sprawdź czy są pliki .msf lub bez rozszerzenia (mbox)
                                        if os.path.isfile(item_path):
                                            size_mb = os.path.getsize(item_path) / (1024*1024)
                                            print(f"           Rozmiar: {size_mb:.2f} MB")
    else:
        print(f"✗ Nie znaleziono: {base_path}")
