"""
CallCryptor Source Scanner
==========================

Skanuje źródła nagrań (foldery lokalne i konta email) w poszukiwaniu plików audio.

Features:
- Skanowanie folderów lokalnych (rekurencyjne z kontrolą głębokości)
- Skanowanie skrzynek email (IMAP + załączniki)
- Ekstrakcja metadanych audio (duration, format, bitrate)
- Deduplication przez hash plików
- Progress reporting
"""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from loguru import logger
import imaplib
import email
from email.header import decode_header
import re


class FolderScanner:
    """Scanner dla folderów lokalnych"""
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: CallCryptorDatabase instance
        """
        self.db_manager = db_manager
        self.progress_callback: Optional[Callable] = None
    
    def scan_folder(
        self,
        source_id: str,
        folder_path: str,
        extensions: List[str],
        max_depth: int = 1,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict:
        """
        Skanuj folder w poszukiwaniu plików audio.
        
        Args:
            source_id: ID źródła w bazie
            folder_path: Ścieżka do folderu
            extensions: Lista rozszerzeń (bez kropki, np. ['mp3', 'wav'])
            max_depth: Maksymalna głębokość skanowania (1 = tylko główny folder)
            progress_callback: Callback(current, total, filename)
            
        Returns:
            Dict z wynikami: {
                'found': int,
                'added': int,
                'duplicates': int,
                'errors': List[str]
            }
        """
        self.progress_callback = progress_callback
        
        results = {
            'found': 0,
            'added': 0,
            'duplicates': 0,
            'errors': []
        }
        
        if not os.path.exists(folder_path):
            results['errors'].append(f"Folder nie istnieje: {folder_path}")
            logger.error(f"[FolderScanner] Folder not found: {folder_path}")
            return results
        
        logger.info(f"[FolderScanner] Scanning: {folder_path}, depth={max_depth}, extensions={extensions}")
        
        # Zbierz wszystkie pliki
        audio_files = self._find_audio_files(folder_path, extensions, max_depth)
        results['found'] = len(audio_files)
        
        logger.info(f"[FolderScanner] Found {len(audio_files)} audio files")
        
        # Pobierz źródło z bazy
        source = self.db_manager.get_source(source_id)
        if not source:
            results['errors'].append(f"Źródło nie znalezione: {source_id}")
            return results
        
        user_id = source['user_id']
        
        # Przetwórz każdy plik
        for i, file_path in enumerate(audio_files, 1):
            if progress_callback:
                progress_callback(i, len(audio_files), os.path.basename(file_path))
            
            try:
                # Oblicz hash
                file_hash = self._calculate_file_hash(file_path)
                
                # Sprawdź czy już istnieje
                if self.db_manager.recording_exists_by_hash(file_hash, user_id):
                    results['duplicates'] += 1
                    logger.debug(f"[FolderScanner] Duplicate: {file_path}")
                    continue
                
                # Pobierz metadane
                metadata = self._extract_metadata(file_path)
                
                # Dodaj do bazy
                recording_data = {
                    'source_id': source_id,
                    'file_name': os.path.basename(file_path),
                    'file_path': str(file_path),
                    'file_size': os.path.getsize(file_path),
                    'file_hash': file_hash,
                    'file_format': metadata.get('format'),
                    'duration_seconds': metadata.get('duration'),
                    'contact_name': metadata.get('contact_name'),
                    'contact_phone': metadata.get('contact_phone'),
                    'recording_date': metadata.get('call_date'),  # Data z metadanych pliku
                    'call_type': metadata.get('call_type', 'unknown')
                }
                
                self.db_manager.add_recording(recording_data, user_id)
                results['added'] += 1
                logger.debug(f"[FolderScanner] Added: {file_path}")
                
            except Exception as e:
                error_msg = f"Błąd przetwarzania {file_path}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(f"[FolderScanner] {error_msg}")
        
        # Aktualizuj licznik nagrań w źródle
        self.db_manager.update_source_stats(source_id, results['added'])
        
        logger.success(f"[FolderScanner] Scan complete: {results}")
        return results
    
    def _find_audio_files(
        self,
        folder_path: str,
        extensions: List[str],
        max_depth: int,
        current_depth: int = 0
    ) -> List[str]:
        """
        Znajdź pliki audio w folderze (rekurencyjnie).
        
        Args:
            folder_path: Ścieżka do folderu
            extensions: Lista rozszerzeń
            max_depth: Maksymalna głębokość
            current_depth: Obecna głębokość (0 = główny folder)
            
        Returns:
            Lista ścieżek do plików audio
        """
        audio_files = []
        
        try:
            # Normalizuj rozszerzenia (małe litery, bez kropki)
            extensions = [ext.lower().strip('.') for ext in extensions]
            
            # Iteruj po zawartości folderu
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                
                # Plik - sprawdź rozszerzenie
                if os.path.isfile(item_path):
                    file_ext = os.path.splitext(item)[1].lower().strip('.')
                    if file_ext in extensions:
                        audio_files.append(item_path)
                
                # Folder - skanuj rekurencyjnie jeśli nie przekroczono głębokości
                elif os.path.isdir(item_path) and current_depth < max_depth:
                    subfolder_files = self._find_audio_files(
                        item_path,
                        extensions,
                        max_depth,
                        current_depth + 1
                    )
                    audio_files.extend(subfolder_files)
        
        except PermissionError as e:
            logger.warning(f"[FolderScanner] Permission denied: {folder_path}")
        except Exception as e:
            logger.error(f"[FolderScanner] Error scanning {folder_path}: {e}")
        
        return audio_files
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Oblicz SHA256 hash pliku"""
        sha256 = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                # Czytaj plik w kawałkach (nie ładuj całego do pamięci)
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            
            return sha256.hexdigest()
        
        except Exception as e:
            logger.error(f"[FolderScanner] Hash calculation failed for {file_path}: {e}")
            # Fallback - hash nazwy pliku + rozmiaru
            return hashlib.sha256(f"{file_path}_{os.path.getsize(file_path)}".encode()).hexdigest()
    
    def _extract_metadata(self, file_path: str) -> Dict:
        """
        Wydobądź metadane z pliku audio.
        
        Returns:
            Dict z metadanymi: {
                'format': str,
                'duration': int (seconds),
                'contact_name': str,
                'contact_phone': str,
                'call_date': str (ISO),
                'call_type': str
            }
        """
        metadata = {
            'format': os.path.splitext(file_path)[1].strip('.').upper(),
            'duration': None,
            'contact_name': None,
            'contact_phone': None,
            'call_date': None,
            'call_type': 'unknown'
        }
        
        # Próbuj wydobyć informacje z nazwy pliku
        # Wspólne formaty nazw: "Contact_20231108_143022.mp3", "123456789_incoming.wav"
        filename = os.path.basename(file_path)
        
        # Szukaj numeru telefonu
        phone_match = re.search(r'\d{9,}', filename)
        if phone_match:
            metadata['contact_phone'] = phone_match.group()
        
        # Szukaj daty (YYYYMMDD lub YYYY-MM-DD)
        date_match = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', filename)
        if date_match:
            try:
                year, month, day = date_match.groups()
                metadata['call_date'] = f"{year}-{month}-{day}"
            except:
                pass
        
        # Jeśli nie znaleziono daty w nazwie, użyj daty utworzenia pliku
        if not metadata['call_date']:
            try:
                # Windows: creation time, Unix: ostatnia modyfikacja metadanych
                file_stat = os.stat(file_path)
                # Użyj starszej z dat: creation (st_ctime) lub modification (st_mtime)
                # st_ctime na Windows = data utworzenia, na Unix = zmiana metadanych
                # st_mtime = data ostatniej modyfikacji zawartości
                # Dla nagrań najlepiej użyć st_mtime (data rzeczywistego utworzenia nagrania)
                file_timestamp = file_stat.st_mtime
                file_date = datetime.fromtimestamp(file_timestamp)
                metadata['call_date'] = file_date.isoformat()
            except Exception as e:
                logger.warning(f"[FolderScanner] Cannot extract file date from {file_path}: {e}")
        
        # Szukaj typu połączenia
        if 'incoming' in filename.lower() or 'przychodzace' in filename.lower():
            metadata['call_type'] = 'incoming'
        elif 'outgoing' in filename.lower() or 'wychodzace' in filename.lower():
            metadata['call_type'] = 'outgoing'
        
        # TODO: Użyj mutagen/tinytag do ekstrakcji duration
        # Na razie zwróć podstawowe metadane
        
        return metadata


class EmailScanner:
    """Scanner dla kont email (IMAP)"""
    
    def __init__(self, db_manager):
        """
        Args:
            db_manager: CallCryptorDatabase instance
        """
        self.db_manager = db_manager
        self.progress_callback: Optional[Callable] = None
    
    def scan_email_account(
        self,
        source_id: str,
        email_config: Dict,
        search_phrase: str,
        target_folder: str = 'INBOX',
        attachment_pattern: str = r'.*\.(mp3|wav|m4a|ogg|flac)$',
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        preview_only: bool = False,
        date_range: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Skanuj konto email w poszukiwaniu załączników audio.
        
        Args:
            source_id: ID źródła
            email_config: Konfiguracja email (z EmailAccountsDatabase.get_account_config)
            search_phrase: Fraza wyszukiwania (np. "FROM recorder@example.com")
            target_folder: Folder IMAP (domyślnie INBOX)
            attachment_pattern: Regex dla nazw załączników
            progress_callback: Callback(current, total, subject)
            preview_only: Jeśli True, zwróć tylko podgląd bez pobierania załączników
            date_range: Opcjonalny zakres dat {'from': 'DD-Mon-YYYY', 'to': 'DD-Mon-YYYY'}
            
        Returns:
            Dict z wynikami:
            - preview_only=True: {'total_messages': int, 'date_range': {'oldest': str, 'newest': str}}
            - preview_only=False: {'found': int, 'added': int, 'duplicates': int, 'errors': List[str]}
        """
        self.progress_callback = progress_callback
        
        results = {
            'found': 0,
            'added': 0,
            'duplicates': 0,
            'errors': []
        }
        
        logger.info(f"[EmailScanner] Connecting to {email_config['server_address']}...")
        
        try:
            # Połącz z serwerem IMAP
            if email_config.get('use_ssl', True):
                mail = imaplib.IMAP4_SSL(
                    email_config['server_address'],
                    email_config['server_port']
                )
            else:
                mail = imaplib.IMAP4(
                    email_config['server_address'],
                    email_config['server_port']
                )
            
            # Zaloguj się
            mail.login(email_config['username'], email_config['password'])
            logger.info(f"[EmailScanner] Logged in as {email_config['username']}")
            
            # Pobierz źródło z bazy
            source = self.db_manager.get_source(source_id)
            if not source:
                results['errors'].append(f"Źródło nie znalezione: {source_id}")
                return results
            
            user_id = source['user_id']
            pattern = re.compile(attachment_pattern, re.IGNORECASE)
            
            # Określ foldery do przeszukania
            folders_to_scan = []
            search_all = source.get('search_all_folders', False)
            
            if search_all or target_folder == '*':
                # Pobierz listę wszystkich folderów (jak w email_monitor.py)
                try:
                    _, folder_list = mail.list()
                    logger.debug(f"[EmailScanner] Raw folder list response: {folder_list}")
                    
                    for folder_line in folder_list:
                        # Parse folder name from IMAP LIST response
                        # Format: (flags) "delimiter" "folder_name"
                        folder_line_str = "<unable to decode>"
                        try:
                            folder_line_str = folder_line.decode('utf-8', errors='ignore') if isinstance(folder_line, bytes) else str(folder_line)
                            logger.debug(f"[EmailScanner] Processing folder line: {repr(folder_line_str)}")
                            
                            # Parsowanie folderów IMAP
                            # Format 1: (flags) "/" "folder_name"  -> w cudzysłowach
                            # Format 2: (flags) "/" folder_name    -> BEZ cudzysłowów
                            parts = folder_line_str.split('"')
                            
                            if len(parts) >= 5:
                                # Format z cudzysłowami: parts = ['(flags) ', '/', ' ', 'folder_name', '']
                                folder_name = parts[-2]  # Przedostatni element (nazwa folderu)
                                logger.debug(f"[EmailScanner] Extracted from quotes: '{folder_name}'")
                            else:
                                # Format BEZ cudzysłowów - nazwa folderu jest ostatnim słowem
                                # Przykład: (\\HasNoChildren) "/" rozmowy -> ['rozmowy']
                                words = folder_line_str.split()
                                if words:
                                    folder_name = words[-1]  # Ostatnie słowo
                                    logger.debug(f"[EmailScanner] Extracted without quotes: '{folder_name}'")
                                else:
                                    folder_name = None
                            
                            # Dodaj folder jeśli to nie delimiter
                            if folder_name and folder_name not in ['/', '.', '\\']:
                                folders_to_scan.append(folder_name)
                                logger.info(f"[EmailScanner] ✓ Added folder: '{folder_name}'")
                            else:
                                logger.debug(f"[EmailScanner] ✗ Skipped delimiter: '{folder_name}'")
                                
                        except Exception as e:
                            logger.warning(f"[EmailScanner] Failed to parse folder line: {folder_line_str}: {e}")
                            continue
                            
                    logger.info(f"[EmailScanner] Scanning all {len(folders_to_scan)} folders: {folders_to_scan}")
                except Exception as e:
                    logger.error(f"[EmailScanner] Failed to list folders: {e}")
                    folders_to_scan = [target_folder]
            else:
                folders_to_scan = [target_folder]
            
            # Buduj komendę wyszukiwania (jak w email_monitor.py)
            search_type = source.get('search_type', 'SUBJECT')
            
            # Określ czy użytkownik podał komendę IMAP czy zwykłą frazę
            is_imap_command = any(keyword in search_phrase.upper() for keyword in ['FROM', 'TO', 'SUBJECT', 'BODY', 'TEXT', 'ALL', 'UNSEEN', 'SINCE'])
            
            all_message_ids = []
            
            # Przeszukaj wszystkie foldery
            for folder_idx, folder in enumerate(folders_to_scan):
                # Sprawdź anulowanie przed każdym folderem
                if self.progress_callback:
                    try:
                        self.progress_callback(folder_idx, len(folders_to_scan), f"Skanowanie folderu: {folder}")
                    except InterruptedError:
                        logger.info("[EmailScanner] Scan interrupted by user")
                        mail.logout()
                        return {'found': 0, 'added': 0, 'duplicates': 0, 'errors': ['Anulowano przez użytkownika']}
                
                try:
                    # Wybierz folder
                    status, data = mail.select(folder)
                    if status != 'OK':
                        logger.warning(f"[EmailScanner] Cannot select folder {folder}: {status}")
                        continue
                    
                    logger.info(f"[EmailScanner] Searching folder: {folder}")
                    
                    # === DIAGNOSTYKA: Pokaż ostatnie 10 wiadomości z ich tematami ===
                    try:
                        _, all_messages = mail.search(None, 'ALL')
                        if all_messages[0]:
                            all_msg_nums = all_messages[0].split()
                            # Weź ostatnie 10 (lub mniej jeśli jest mniej wiadomości)
                            recent_msgs = all_msg_nums[-10:] if len(all_msg_nums) > 10 else all_msg_nums
                            logger.info(f"[EmailScanner] DIAGNOSTYKA: Folder ma {len(all_msg_nums)} wiadomości, sprawdzam ostatnie {len(recent_msgs)}:")
                            
                            for msg_num in recent_msgs:
                                try:
                                    _, msg_data = mail.fetch(msg_num, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                                    if msg_data and msg_data[0]:
                                        header = msg_data[0][1].decode('utf-8', errors='ignore') if isinstance(msg_data[0][1], bytes) else str(msg_data[0][1])
                                        # Wyciągnij tylko Subject
                                        for line in header.split('\n'):
                                            if line.lower().startswith('subject:'):
                                                logger.info(f"[EmailScanner]   Msg #{msg_num.decode()}: {line.strip()}")
                                                break
                                except Exception as e:
                                    logger.debug(f"[EmailScanner] Błąd odczytu msg {msg_num}: {e}")
                        else:
                            logger.info(f"[EmailScanner] DIAGNOSTYKA: Folder {folder} jest pusty")
                    except Exception as e:
                        logger.warning(f"[EmailScanner] DIAGNOSTYKA nie powiodła się: {e}")
                    # === KONIEC DIAGNOSTYKI ===
                    
                    # Buduj zapytania - najpierw UNSEEN, potem ostatnie 7 dni (jak w email_monitor.py)
                    from datetime import datetime, timedelta
                    week_ago = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
                    
                    search_queries = []
                    
                    # Dodaj filtr dat jeśli podano
                    date_filter = ""
                    if date_range:
                        if date_range.get('from'):
                            date_filter = f'SINCE {date_range["from"]} '
                        if date_range.get('to'):
                            date_filter += f'BEFORE {date_range["to"]} '
                    
                    if is_imap_command:
                        # Użytkownik podał komendę IMAP - użyj jej bezpośrednio
                        search_queries = [
                            f'{date_filter}UNSEEN {search_phrase}',
                            f'{date_filter}SINCE {week_ago} {search_phrase}'
                        ]
                    else:
                        # Użytkownik podał zwykłą frazę - ZAWSZE użyj cudzysłowów
                        # ZMIANA: Jeśli fraza jest pusta lub bardzo krótka, użyj ALL
                        if not search_phrase or len(search_phrase.strip()) < 2:
                            search_queries = [
                                f'{date_filter}ALL',  # Wszystkie wiadomości
                            ]
                        else:
                            # W trybie preview używamy tylko ALL z date_filter
                            if preview_only:
                                search_queries = [
                                    f'{date_filter}{search_type} "{search_phrase}"'
                                ]
                            else:
                                # Tryb normalny - testuj różne warianty dla lepszego pokrycia
                                search_queries = [
                                    f'{date_filter}UNSEEN {search_type} "{search_phrase}"',
                                    f'{date_filter}{search_type} "{search_phrase}"',  # Wszystkie wiadomości (bez UNSEEN)
                                    f'{date_filter}SINCE {week_ago} {search_type} "{search_phrase}"',
                                    f'{date_filter}ALL'  # Ostateczny fallback - wszystkie wiadomości
                                ]
                    
                    # Wykonaj wyszukiwanie (najpierw UNSEEN, potem wszystkie, na końcu SINCE)
                    found_in_folder = []
                    for search_query in search_queries:
                        try:
                            logger.info(f"[EmailScanner] Search query: {search_query}")
                            _, message_numbers = mail.search(None, search_query)
                            
                            logger.debug(f"[EmailScanner] Raw response: {message_numbers}")
                            
                            if message_numbers[0]:
                                msg_nums = message_numbers[0].split()
                                logger.info(f"[EmailScanner] Found {len(msg_nums)} messages with query: {search_query}")
                                found_in_folder.extend([(msg_id, folder) for msg_id in msg_nums])
                                
                                # Jeśli znaleźliśmy wiadomości, zatrzymaj się (nie sprawdzaj kolejnych wariantów)
                                if msg_nums:
                                    break
                            else:
                                logger.info(f"[EmailScanner] No messages found with query: {search_query}")
                        except Exception as e:
                            logger.warning(f"[EmailScanner] Search query failed '{search_query}': {e}")
                            continue
                    
                    # Usuń duplikaty w tym folderze
                    unique_in_folder = list(set(found_in_folder))
                    all_message_ids.extend(unique_in_folder)
                    logger.info(f"[EmailScanner] Found {len(unique_in_folder)} unique messages in {folder}")
                    
                except Exception as e:
                    logger.warning(f"[EmailScanner] Failed to search folder {folder}: {e}")
                    continue
            
            # Usuń globalne duplikaty
            all_message_ids = list(set(all_message_ids))
            results['found'] = len(all_message_ids)
            logger.info(f"[EmailScanner] Found {len(all_message_ids)} total unique messages across all folders")
            
            # ===== TRYB PREVIEW - tylko zlicz i znajdź zakres dat =====
            if preview_only:
                logger.info(f"[EmailScanner] Preview mode - checking dates for {len(all_message_ids)} messages")
                
                oldest_date = None
                newest_date = None
                
                # Pobierz daty dla kilku wiadomości (pierwszy 10 i ostatnich 10) aby określić zakres
                sample_messages = []
                if len(all_message_ids) <= 20:
                    sample_messages = all_message_ids
                else:
                    # Posortuj po ID (nowsze mają wyższe ID)
                    sorted_msgs = sorted(all_message_ids, key=lambda x: int(x[0]))
                    sample_messages = sorted_msgs[:10] + sorted_msgs[-10:]
                
                for idx, (msg_id, folder) in enumerate(sample_messages):
                    # Sprawdź anulowanie
                    if self.progress_callback:
                        try:
                            self.progress_callback(idx, len(sample_messages), f"Sprawdzanie dat: {idx}/{len(sample_messages)}")
                        except InterruptedError:
                            logger.info("[EmailScanner] Preview interrupted by user")
                            mail.logout()
                            return {'total_messages': 0, 'date_range': {'oldest': None, 'newest': None}}
                    
                    try:
                        mail.select(folder)
                        _, msg_data = mail.fetch(msg_id, '(INTERNALDATE)')
                        
                        if msg_data and msg_data[0]:
                            # msg_data[0] jest tuple (bytes, bytes), weź pierwszy element
                            date_bytes = msg_data[0][0] if isinstance(msg_data[0], tuple) else msg_data[0]
                            date_str = date_bytes.decode('utf-8') if isinstance(date_bytes, bytes) else str(date_bytes)
                            
                            # Przykład: b'1 (INTERNALDATE "17-Jan-2024 12:34:56 +0000")'
                            date_match = re.search(r'INTERNALDATE "([^"]+)"', date_str)
                            if date_match:
                                date_str = date_match.group(1)
                                # Konwertuj do datetime
                                from email.utils import parsedate_to_datetime
                                msg_date = parsedate_to_datetime(date_str)
                                
                                if oldest_date is None or msg_date < oldest_date:
                                    oldest_date = msg_date
                                if newest_date is None or msg_date > newest_date:
                                    newest_date = msg_date
                    except Exception as e:
                        logger.debug(f"[EmailScanner] Error getting date for message {msg_id}: {e}")
                
                mail.logout()
                
                return {
                    'total_messages': len(all_message_ids),
                    'date_range': {
                        'oldest': oldest_date.strftime('%d-%b-%Y') if oldest_date else None,
                        'newest': newest_date.strftime('%d-%b-%Y') if newest_date else None
                    }
                }
            
            # ===== TRYB NORMALNY - pobieraj załączniki =====
            # OPTYMALIZACJA: Ogranicz do maksymalnie 200 najnowszych wiadomości
            MAX_MESSAGES = 200
            if len(all_message_ids) > MAX_MESSAGES:
                logger.warning(f"[EmailScanner] Limiting scan to {MAX_MESSAGES} newest messages (found {len(all_message_ids)})")
                # Sortuj malejąco po ID (nowsze mają wyższe ID) i weź pierwsze MAX_MESSAGES
                all_message_ids = sorted(all_message_ids, key=lambda x: int(x[0]), reverse=True)[:MAX_MESSAGES]
            
            # Przetwórz każdą wiadomość
            for i, (msg_id, folder) in enumerate(all_message_ids, 1):
                # Upewnij się, że jesteśmy we właściwym folderze
                mail.select(folder)
                
                if progress_callback:
                    try:
                        progress_callback(i, len(all_message_ids), f"{folder}: Message {i}/{len(all_message_ids)}")
                    except InterruptedError:
                        logger.info("[EmailScanner] Download interrupted by user")
                        mail.logout()
                        return results
                
                try:
                    # Pobierz wiadomość
                    _, msg_data = mail.fetch(msg_id, '(RFC822)')
                    if not msg_data or not msg_data[0]:
                        continue
                    
                    email_body = msg_data[0][1]
                    if not isinstance(email_body, bytes):
                        continue
                        
                    message = email.message_from_bytes(email_body)
                    
                    # Pobierz temat
                    subject = self._decode_header(message.get('Subject', ''))
                    
                    # Szukaj załączników
                    for part in message.walk():
                        if part.get_content_maintype() == 'multipart':
                            continue
                        if part.get('Content-Disposition') is None:
                            continue
                        
                        filename = part.get_filename()
                        if filename and pattern.match(filename):
                            # Dekoduj nazwę pliku
                            filename = self._decode_header(filename)
                            
                            # Pobierz dane załącznika
                            attachment_data = part.get_payload(decode=True)
                            if not isinstance(attachment_data, bytes):
                                continue
                            
                            # Oblicz hash
                            file_hash = hashlib.sha256(attachment_data).hexdigest()
                            
                            # Sprawdź duplikat
                            if self.db_manager.recording_exists_by_hash(file_hash, user_id):
                                results['duplicates'] += 1
                                continue
                            
                            # Zapisz załącznik lokalnie
                            from ...core.config import config
                            recordings_dir = config.DATA_DIR / "recordings"
                            recordings_dir.mkdir(exist_ok=True)
                            
                            # Unikalna nazwa pliku: hash[:8]_original_name
                            safe_filename = f"{file_hash[:8]}_{filename}"
                            file_path = recordings_dir / safe_filename
                            
                            with open(file_path, 'wb') as f:
                                f.write(attachment_data)
                            
                            # Pobierz datę wiadomości
                            date_str = message.get('Date', '')
                            email_date = None
                            if date_str:
                                from email.utils import parsedate_to_datetime
                                try:
                                    email_date = parsedate_to_datetime(date_str).isoformat()
                                except:
                                    pass
                            
                            # Parsuj nazwę kontaktu z tematu (usuń pomijane słowa)
                            contact_name = self._parse_contact_name(subject, source)
                            
                            # Dodaj do bazy
                            recording_data = {
                                'source_id': source_id,
                                'file_name': filename,
                                'file_path': str(file_path),
                                'file_size': len(attachment_data),
                                'file_hash': file_hash,
                                'file_format': os.path.splitext(filename)[1].strip('.').upper(),
                                'duration_seconds': None,  # Nie znamy długości z emaila
                                'contact_name': contact_name,
                                'contact_phone': None,
                                'recording_date': email_date,  # Data z nagłówka emaila
                                'call_type': 'email'
                            }
                            
                            self.db_manager.add_recording(recording_data, user_id)
                            results['added'] += 1
                            logger.debug(f"[EmailScanner] Added: {filename} -> {file_path}")
                
                except Exception as e:
                    error_msg = f"Błąd przetwarzania wiadomości {msg_id}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(f"[EmailScanner] {error_msg}")
            
            # Wyloguj
            mail.logout()
            
            # Aktualizuj licznik nagrań w źródle (tylko jeśli nie preview)
            if not preview_only:
                self.db_manager.update_source_stats(source_id, results['added'])
            
            logger.success(f"[EmailScanner] Scan complete: {results}")
        
        except Exception as e:
            error_msg = f"Błąd połączenia email: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(f"[EmailScanner] {error_msg}")
        
        return results
    
    def _decode_header(self, header_value: str) -> str:
        """Dekoduj nagłówek email"""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part
        
        return decoded_string
    
    def _parse_contact_name(self, subject: str, source: Dict) -> str:
        """
        Parsuj nazwę kontaktu z tematu emaila, usuwając pomijane słowa.
        
        Args:
            subject: Temat wiadomości email
            source: Dict z konfiguracją źródła (zawiera contact_ignore_words)
            
        Returns:
            Oczyszczona nazwa kontaktu
        """
        if not subject:
            return "Unknown"
        
        contact_name = subject.strip()
        
        # Pobierz listę pomijanych słów
        ignore_words_str = source.get('contact_ignore_words', '')
        if not ignore_words_str:
            return contact_name
        
        # Podziel na słowa/frazy (średnik jako separator)
        ignore_phrases = [phrase.strip() for phrase in ignore_words_str.split(';') if phrase.strip()]
        
        # Usuń każdą frazę (case-insensitive)
        for phrase in ignore_phrases:
            if phrase:
                # Użyj re.IGNORECASE dla ignorowania wielkości liter
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                contact_name = pattern.sub('', contact_name)
        
        # Wyczyść nadmiarowe spacje i znaki
        contact_name = re.sub(r'\s+', ' ', contact_name).strip()
        contact_name = contact_name.strip('- :,')
        
        # Jeśli zostanie puste, użyj "Unknown"
        if not contact_name:
            return "Unknown"
        
        return contact_name
