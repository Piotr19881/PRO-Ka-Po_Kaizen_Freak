"""
Email Helper - Universal Email Connector
==========================================

Uniwersalny connector do obsługi kont e-mail (IMAP/POP3).
Używany przez moduł CallCryptor do skanowania skrzynek pocztowych
w poszukiwaniu nagrań.

Features:
- IMAP i POP3 support
- Multi-account management
- Search messages by criteria
- Download attachments
- SSL/TLS support

Usage:
    connector = EmailConnector(account_config)
    if connector.connect():
        messages = connector.search_messages(
            folder="INBOX",
            search_criteria={'subject': 'nagranie'}
        )
        for msg in messages:
            connector.download_all_attachments(msg['message_id'], save_dir)
        connector.disconnect()
"""

import imaplib
import poplib
import email
from email.header import decode_header
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from loguru import logger
import re
import hashlib


class EmailConnectionError(Exception):
    """Wyjątek dla błędów połączenia z serwerem e-mail"""
    pass


class EmailConnector:
    """
    Uniwersalny connector do kont e-mail.
    Obsługuje IMAP i POP3 z pełnym wsparciem dla SSL/TLS.
    """
    
    def __init__(self, account_config: dict):
        """
        Inicjalizacja connectora.
        
        Args:
            account_config: {
                'account_id': str,           # Unique ID konta
                'server_type': 'IMAP' | 'POP3',
                'server_address': str,
                'server_port': int,
                'username': str,
                'password': str,
                'use_ssl': bool,
                'use_tls': bool (optional)
            }
        """
        self.config = account_config
        self.connection = None
        self.connected = False
        
        # Validate config
        required_fields = ['server_type', 'server_address', 'server_port', 'username', 'password']
        for field in required_fields:
            if field not in account_config:
                raise ValueError(f"Missing required field: {field}")
        
        # Normalize server type
        self.server_type = account_config['server_type'].upper()
        if self.server_type not in ['IMAP', 'POP3']:
            raise ValueError(f"Unsupported server type: {self.server_type}")
    
    # =========================================================================
    # CONNECTION MANAGEMENT
    # =========================================================================
    
    def connect(self) -> bool:
        """
        Nawiąż połączenie z serwerem e-mail.
        
        Returns:
            True jeśli połączenie udane, False w przeciwnym razie
        """
        try:
            if self.server_type == 'IMAP':
                return self._connect_imap()
            else:
                return self._connect_pop3()
        except Exception as e:
            logger.error(f"[EmailConnector] Connection failed: {e}")
            self.connected = False
            return False
    
    def _connect_imap(self) -> bool:
        """Połączenie IMAP"""
        try:
            server = self.config['server_address']
            port = self.config['server_port']
            use_ssl = self.config.get('use_ssl', True)
            
            # Wybierz klasę IMAP
            if use_ssl:
                self.connection = imaplib.IMAP4_SSL(server, port)
                logger.debug(f"[EmailConnector] IMAP SSL connection to {server}:{port}")
            else:
                self.connection = imaplib.IMAP4(server, port)
                logger.debug(f"[EmailConnector] IMAP connection to {server}:{port}")
                
                # STARTTLS if requested
                if self.config.get('use_tls', False):
                    self.connection.starttls()
                    logger.debug("[EmailConnector] STARTTLS enabled")
            
            # Login
            username = self.config['username']
            password = self.config['password']
            self.connection.login(username, password)
            
            self.connected = True
            logger.success(f"[EmailConnector] IMAP connected as {username}")
            return True
            
        except imaplib.IMAP4.error as e:
            logger.error(f"[EmailConnector] IMAP error: {e}")
            raise EmailConnectionError(f"IMAP connection failed: {e}")
        except Exception as e:
            logger.error(f"[EmailConnector] Unexpected error: {e}")
            raise EmailConnectionError(f"Connection failed: {e}")
    
    def _connect_pop3(self) -> bool:
        """Połączenie POP3"""
        try:
            server = self.config['server_address']
            port = self.config['server_port']
            use_ssl = self.config.get('use_ssl', True)
            
            # Wybierz klasę POP3
            if use_ssl:
                self.connection = poplib.POP3_SSL(server, port)
                logger.debug(f"[EmailConnector] POP3 SSL connection to {server}:{port}")
            else:
                self.connection = poplib.POP3(server, port)
                logger.debug(f"[EmailConnector] POP3 connection to {server}:{port}")
                
                # STARTTLS if requested
                if self.config.get('use_tls', False):
                    self.connection.stls()
                    logger.debug("[EmailConnector] STARTTLS enabled")
            
            # Login
            username = self.config['username']
            password = self.config['password']
            self.connection.user(username)
            self.connection.pass_(password)
            
            self.connected = True
            logger.success(f"[EmailConnector] POP3 connected as {username}")
            return True
            
        except poplib.error_proto as e:
            logger.error(f"[EmailConnector] POP3 error: {e}")
            raise EmailConnectionError(f"POP3 connection failed: {e}")
        except Exception as e:
            logger.error(f"[EmailConnector] Unexpected error: {e}")
            raise EmailConnectionError(f"Connection failed: {e}")
    
    def disconnect(self):
        """Zakończ połączenie z serwerem"""
        if not self.connected or not self.connection:
            return
        
        try:
            if self.server_type == 'IMAP':
                self.connection.logout()
            else:
                self.connection.quit()
            
            logger.info("[EmailConnector] Disconnected")
            self.connected = False
            self.connection = None
            
        except Exception as e:
            logger.warning(f"[EmailConnector] Error during disconnect: {e}")
            self.connected = False
            self.connection = None
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Testuj połączenie z serwerem.
        
        Returns:
            (success: bool, message: str)
        """
        try:
            if self.connect():
                self.disconnect()
                return (True, "Połączenie udane")
            else:
                return (False, "Nie udało się nawiązać połączenia")
        except EmailConnectionError as e:
            return (False, str(e))
        except Exception as e:
            return (False, f"Błąd: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
    
    # =========================================================================
    # IMAP-SPECIFIC METHODS
    # =========================================================================
    
    def get_folders(self) -> List[str]:
        """
        Pobierz listę folderów w skrzynce (tylko IMAP).
        
        Returns:
            Lista nazw folderów
        """
        if self.server_type != 'IMAP':
            logger.warning("[EmailConnector] get_folders() tylko dla IMAP")
            return []
        
        if not self.connected:
            raise EmailConnectionError("Not connected to server")
        
        try:
            status, folders = self.connection.list()
            if status != 'OK':
                logger.error(f"[EmailConnector] Failed to list folders: {status}")
                return []
            
            folder_names = []
            for folder in folders:
                # Parse folder name (format: '(flags) "delimiter" "name"')
                folder_str = folder.decode() if isinstance(folder, bytes) else folder
                match = re.search(r'"([^"]+)"$', folder_str)
                if match:
                    folder_names.append(match.group(1))
            
            logger.debug(f"[EmailConnector] Found {len(folder_names)} folders")
            return folder_names
            
        except Exception as e:
            logger.error(f"[EmailConnector] Error listing folders: {e}")
            return []
    
    def select_folder(self, folder: str = "INBOX") -> bool:
        """
        Wybierz folder do pracy (tylko IMAP).
        
        Args:
            folder: Nazwa folderu
            
        Returns:
            True jeśli sukces
        """
        if self.server_type != 'IMAP':
            return False
        
        if not self.connected:
            raise EmailConnectionError("Not connected to server")
        
        try:
            status, data = self.connection.select(folder)
            if status == 'OK':
                logger.debug(f"[EmailConnector] Selected folder: {folder}")
                return True
            else:
                logger.error(f"[EmailConnector] Failed to select folder: {status}")
                return False
        except Exception as e:
            logger.error(f"[EmailConnector] Error selecting folder: {e}")
            return False
    
    def search_messages(
        self,
        folder: str = "INBOX",
        search_criteria: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Wyszukaj wiadomości spełniające kryteria.
        
        Args:
            folder: Nazwa folderu (dla IMAP)
            search_criteria: {
                'subject': str,         # Szukaj w temacie
                'from': str,            # Nadawca
                'since': date,          # Od daty
                'before': date,         # Do daty
                'has_attachment': bool  # Czy ma załączniki (IMAP only)
            }
            
        Returns:
            Lista wiadomości: [{
                'message_id': str,
                'subject': str,
                'from': str,
                'date': datetime,
                'has_attachments': bool,
                'attachment_count': int,
                'attachment_names': List[str]
            }]
        """
        if self.server_type == 'IMAP':
            return self._search_imap(folder, search_criteria)
        else:
            return self._search_pop3(search_criteria)
    
    def _search_imap(
        self,
        folder: str,
        search_criteria: Optional[Dict]
    ) -> List[Dict]:
        """Wyszukiwanie IMAP"""
        if not self.connected:
            raise EmailConnectionError("Not connected to server")
        
        # Wybierz folder
        if not self.select_folder(folder):
            return []
        
        # Build search query
        search_parts = []
        if search_criteria:
            if 'subject' in search_criteria:
                search_parts.append(f'SUBJECT "{search_criteria["subject"]}"')
            if 'from' in search_criteria:
                search_parts.append(f'FROM "{search_criteria["from"]}"')
            if 'since' in search_criteria:
                date_str = search_criteria['since'].strftime('%d-%b-%Y')
                search_parts.append(f'SINCE {date_str}')
            if 'before' in search_criteria:
                date_str = search_criteria['before'].strftime('%d-%b-%Y')
                search_parts.append(f'BEFORE {date_str}')
        
        # Default: ALL
        search_query = ' '.join(search_parts) if search_parts else 'ALL'
        
        try:
            status, message_numbers = self.connection.search(None, search_query)
            if status != 'OK':
                logger.error(f"[EmailConnector] Search failed: {status}")
                return []
            
            message_ids = message_numbers[0].split()
            logger.info(f"[EmailConnector] Found {len(message_ids)} messages")
            
            # Fetch message details
            messages = []
            for msg_id in message_ids:
                msg_data = self._fetch_message_imap(msg_id)
                if msg_data:
                    # Filter by has_attachment if specified
                    if search_criteria and 'has_attachment' in search_criteria:
                        if search_criteria['has_attachment'] != msg_data['has_attachments']:
                            continue
                    messages.append(msg_data)
            
            return messages
            
        except Exception as e:
            logger.error(f"[EmailConnector] Error searching messages: {e}")
            return []
    
    def _fetch_message_imap(self, message_id: bytes) -> Optional[Dict]:
        """Pobierz szczegóły wiadomości IMAP"""
        try:
            status, msg_data = self.connection.fetch(message_id, '(RFC822)')
            if status != 'OK':
                return None
            
            # Parse email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Extract headers
            subject = self._decode_header(email_message.get('Subject', ''))
            from_addr = self._decode_header(email_message.get('From', ''))
            date_str = email_message.get('Date', '')
            
            # Parse date
            try:
                msg_date = email.utils.parsedate_to_datetime(date_str)
            except:
                msg_date = datetime.now()
            
            # Check for attachments
            attachments = []
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename:
                    attachments.append(self._decode_header(filename))
            
            return {
                'message_id': message_id.decode(),
                'subject': subject,
                'from': from_addr,
                'date': msg_date,
                'has_attachments': len(attachments) > 0,
                'attachment_count': len(attachments),
                'attachment_names': attachments
            }
            
        except Exception as e:
            logger.error(f"[EmailConnector] Error fetching message {message_id}: {e}")
            return None
    
    def _search_pop3(self, search_criteria: Optional[Dict]) -> List[Dict]:
        """Wyszukiwanie POP3 (pobiera wszystkie i filtruje lokalnie)"""
        if not self.connected:
            raise EmailConnectionError("Not connected to server")
        
        try:
            # Get message count
            num_messages = len(self.connection.list()[1])
            logger.info(f"[EmailConnector] POP3: {num_messages} messages on server")
            
            messages = []
            for i in range(1, num_messages + 1):
                # Fetch message
                response, lines, octets = self.connection.retr(i)
                raw_email = b'\n'.join(lines)
                email_message = email.message_from_bytes(raw_email)
                
                # Extract headers
                subject = self._decode_header(email_message.get('Subject', ''))
                from_addr = self._decode_header(email_message.get('From', ''))
                date_str = email_message.get('Date', '')
                
                # Parse date
                try:
                    msg_date = email.utils.parsedate_to_datetime(date_str)
                except:
                    msg_date = datetime.now()
                
                # Apply filters
                if search_criteria:
                    if 'subject' in search_criteria:
                        if search_criteria['subject'].lower() not in subject.lower():
                            continue
                    if 'from' in search_criteria:
                        if search_criteria['from'].lower() not in from_addr.lower():
                            continue
                    if 'since' in search_criteria:
                        if msg_date.date() < search_criteria['since']:
                            continue
                    if 'before' in search_criteria:
                        if msg_date.date() > search_criteria['before']:
                            continue
                
                # Check for attachments
                attachments = []
                for part in email_message.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    if part.get('Content-Disposition') is None:
                        continue
                    
                    filename = part.get_filename()
                    if filename:
                        attachments.append(self._decode_header(filename))
                
                # Apply has_attachment filter
                if search_criteria and 'has_attachment' in search_criteria:
                    if search_criteria['has_attachment'] != (len(attachments) > 0):
                        continue
                
                messages.append({
                    'message_id': str(i),
                    'subject': subject,
                    'from': from_addr,
                    'date': msg_date,
                    'has_attachments': len(attachments) > 0,
                    'attachment_count': len(attachments),
                    'attachment_names': attachments
                })
            
            logger.info(f"[EmailConnector] POP3: {len(messages)} messages matched criteria")
            return messages
            
        except Exception as e:
            logger.error(f"[EmailConnector] Error searching POP3 messages: {e}")
            return []
    
    # =========================================================================
    # ATTACHMENT HANDLING
    # =========================================================================
    
    def download_attachment(
        self,
        message_id: str,
        attachment_name: str,
        save_path: str
    ) -> bool:
        """
        Pobierz załącznik i zapisz do pliku.
        
        Args:
            message_id: ID wiadomości
            attachment_name: Nazwa załącznika
            save_path: Ścieżka docelowa
            
        Returns:
            True jeśli sukces
        """
        try:
            # Fetch message
            if self.server_type == 'IMAP':
                status, msg_data = self.connection.fetch(message_id.encode(), '(RFC822)')
                if status != 'OK':
                    return False
                raw_email = msg_data[0][1]
            else:
                response, lines, octets = self.connection.retr(int(message_id))
                raw_email = b'\n'.join(lines)
            
            email_message = email.message_from_bytes(raw_email)
            
            # Find attachment
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename and self._decode_header(filename) == attachment_name:
                    # Save attachment
                    with open(save_path, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    
                    logger.info(f"[EmailConnector] Downloaded: {attachment_name}")
                    return True
            
            logger.warning(f"[EmailConnector] Attachment not found: {attachment_name}")
            return False
            
        except Exception as e:
            logger.error(f"[EmailConnector] Error downloading attachment: {e}")
            return False
    
    def download_all_attachments(
        self,
        message_id: str,
        save_dir: str,
        pattern: Optional[str] = None
    ) -> List[str]:
        """
        Pobierz wszystkie załączniki z wiadomości.
        
        Args:
            message_id: ID wiadomości
            save_dir: Katalog docelowy
            pattern: Regex pattern dla filtrowania nazw (opcjonalnie)
            
        Returns:
            Lista ścieżek pobranych plików
        """
        downloaded_files = []
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Fetch message
            if self.server_type == 'IMAP':
                status, msg_data = self.connection.fetch(message_id.encode(), '(RFC822)')
                if status != 'OK':
                    return []
                raw_email = msg_data[0][1]
            else:
                response, lines, octets = self.connection.retr(int(message_id))
                raw_email = b'\n'.join(lines)
            
            email_message = email.message_from_bytes(raw_email)
            
            # Process attachments
            regex_pattern = re.compile(pattern) if pattern else None
            
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if not filename:
                    continue
                
                filename = self._decode_header(filename)
                
                # Apply pattern filter
                if regex_pattern and not regex_pattern.search(filename):
                    continue
                
                # Generate unique filename if exists
                file_path = save_path / filename
                counter = 1
                while file_path.exists():
                    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
                    new_name = f"{name}_{counter}.{ext}" if ext else f"{name}_{counter}"
                    file_path = save_path / new_name
                    counter += 1
                
                # Save attachment
                with open(file_path, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                downloaded_files.append(str(file_path))
                logger.debug(f"[EmailConnector] Downloaded: {filename}")
            
            logger.info(f"[EmailConnector] Downloaded {len(downloaded_files)} attachments")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"[EmailConnector] Error downloading attachments: {e}")
            return downloaded_files
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _decode_header(self, header: str) -> str:
        """Dekoduj header e-maila"""
        if not header:
            return ""
        
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
                except:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(part)
        
        return ''.join(decoded_parts)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def test_email_connection(account_config: dict) -> Tuple[bool, str]:
    """
    Testuj połączenie z kontem e-mail.
    
    Args:
        account_config: Konfiguracja konta
        
    Returns:
        (success: bool, message: str)
    """
    try:
        connector = EmailConnector(account_config)
        return connector.test_connection()
    except Exception as e:
        return (False, f"Błąd: {e}")


def get_account_info(account_config: dict) -> Optional[Dict]:
    """
    Pobierz informacje o koncie e-mail.
    
    Returns: {
        'folders': List[str],  # Tylko IMAP
        'message_count': int,
        'server_type': str
    }
    """
    try:
        with EmailConnector(account_config) as connector:
            info = {
                'server_type': connector.server_type
            }
            
            if connector.server_type == 'IMAP':
                info['folders'] = connector.get_folders()
                connector.select_folder('INBOX')
                status, data = connector.connection.search(None, 'ALL')
                info['message_count'] = len(data[0].split()) if status == 'OK' else 0
            else:
                info['folders'] = []
                info['message_count'] = len(connector.connection.list()[1])
            
            return info
            
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return None
