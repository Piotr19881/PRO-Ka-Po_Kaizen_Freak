"""
Zarządzanie podpisami, formatowaniem i operacje pomocnicze dla komponowania wiadomości

Funkcje:
- Ładowanie i zarządzanie podpisami
- Zbieranie adresów email (autouzupełnianie)
- Ładowanie kont nadawcy
- Wstawianie podpisów
- Formatowanie tekstu (bold, italic, underline)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import QTextEdit


def load_signatures_from_disk() -> List[Dict[str, Any]]:
    """Wczytuje podpisy z pliku"""
    signatures_file = Path("mail_client/mail_signatures.json")
    if signatures_file.exists():
        try:
            with open(signatures_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def collect_email_addresses(mail_view_parent=None) -> List[str]:
    """Zbiera wszystkie unikalne adresy email z różnych źródeł"""
    emails = set()
    
    # Z kont email
    accounts_file = Path("mail_client/mail_accounts.json")
    if accounts_file.exists():
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                for account in accounts:
                    if "email" in account:
                        emails.add(account["email"])
        except Exception:
            pass
    
    # Z wiadomości (nadawcy i odbiorcy) jeśli jest dostęp do parent
    if mail_view_parent and hasattr(mail_view_parent, "sample_mails"):
        for folder_mails in mail_view_parent.sample_mails.values():
            for mail in folder_mails:
                # Dodaj nadawcę
                if "from" in mail:
                    from_addr = mail["from"]
                    if "<" in from_addr and ">" in from_addr:
                        email_part = from_addr.split("<")[1].split(">")[0].strip()
                        emails.add(email_part)
                    else:
                        emails.add(from_addr.strip())
                
                # Dodaj odbiorców
                if "to" in mail:
                    to_addr = mail["to"]
                    if to_addr:
                        if "<" in to_addr and ">" in to_addr:
                            email_part = to_addr.split("<")[1].split(">")[0].strip()
                            emails.add(email_part)
                        else:
                            emails.add(to_addr.strip())
    
    # Z prawdziwych maili
    if mail_view_parent and hasattr(mail_view_parent, "real_mails"):
        for account_mails in mail_view_parent.real_mails.values():
            for mail in account_mails:
                if "from" in mail:
                    from_addr = mail["from"]
                    if "<" in from_addr and ">" in from_addr:
                        email_part = from_addr.split("<")[1].split(">")[0].strip()
                        emails.add(email_part)
                    else:
                        emails.add(from_addr.strip())
    
    return sorted(list(emails))


def load_sender_accounts() -> List[Dict[str, str]]:
    """Wczytuje konta email dla pola Od"""
    accounts_file = Path("mail_client/mail_accounts.json")
    result = []
    
    if accounts_file.exists():
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                for account in accounts:
                    if "email" in account:
                        name = account.get("name", account["email"])
                        if name and name != account["email"]:
                            display_text = f"{name} <{account['email']}>"
                        else:
                            display_text = account["email"]
                        result.append({"display": display_text, "email": account["email"]})
        except Exception:
            pass
    
    return result


def insert_signature_into_body(body_field: QTextEdit, signature: str) -> None:
    """Wstawia podpis do treści wiadomości"""
    # Pobierz aktualną treść
    current_text = body_field.toPlainText()
    
    # Usuń poprzedni podpis jeśli istnieje
    separator = "\n\n-- \n"
    if separator in current_text:
        current_text = current_text.split(separator)[0]
    
    # Dodaj nowy podpis
    new_text = current_text + separator + signature
    body_field.setPlainText(new_text)
    
    # Przesuń kursor przed podpis
    cursor = body_field.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Start)
    body_field.setTextCursor(cursor)


def find_default_signature(signatures: List[Dict[str, Any]]) -> Optional[str]:
    """Znajduje domyślny podpis"""
    for sig in signatures:
        if sig.get('default', False):
            return sig.get('content')
    return None


def apply_text_format_bold(text_edit: QTextEdit) -> None:
    """Stosuje pogrubienie do zaznaczonego tekstu"""
    cursor = text_edit.textCursor()
    fmt = cursor.charFormat()
    font = fmt.font()
    font.setBold(not font.bold())
    fmt.setFont(font)
    cursor.mergeCharFormat(fmt)


def apply_text_format_italic(text_edit: QTextEdit) -> None:
    """Stosuje kursywę do zaznaczonego tekstu"""
    cursor = text_edit.textCursor()
    fmt = cursor.charFormat()
    font = fmt.font()
    font.setItalic(not font.italic())
    fmt.setFont(font)
    cursor.mergeCharFormat(fmt)


def apply_text_format_underline(text_edit: QTextEdit) -> None:
    """Stosuje podkreślenie do zaznaczonego tekstu"""
    cursor = text_edit.textCursor()
    fmt = cursor.charFormat()
    font = fmt.font()
    font.setUnderline(not font.underline())
    fmt.setFont(font)
    cursor.mergeCharFormat(fmt)


def change_text_font_size(text_edit: QTextEdit, size: int) -> None:
    """Zmienia rozmiar czcionki zaznaczonego tekstu"""
    cursor = text_edit.textCursor()
    fmt = cursor.charFormat()
    font = fmt.font()
    font.setPointSize(size)
    fmt.setFont(font)
    cursor.mergeCharFormat(fmt)
