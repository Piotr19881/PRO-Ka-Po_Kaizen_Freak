"""
Backblaze B2 Service Module
Obsługa uploadu plików do Backblaze B2 Cloud Storage
"""
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger

try:
    from b2sdk.v2 import InMemoryAccountInfo, B2Api, UploadSourceBytes
except ImportError:
    # Fallback jeśli b2sdk nie jest zainstalowane
    InMemoryAccountInfo = None
    B2Api = None
    UploadSourceBytes = None

try:
    from .config import settings
except ImportError:
    from config import settings


class BackblazeService:
    """Serwis do zarządzania plikami w Backblaze B2"""
    
    def __init__(self):
        self.key_id = settings.B2_APPLICATION_KEY_ID
        self.app_key = settings.B2_APPLICATION_KEY
        self.bucket_name = settings.B2_BUCKET_NAME
        self.bucket_id = settings.B2_BUCKET_ID
        self.download_url = settings.B2_DOWNLOAD_URL
        self.file_expire_days = settings.B2_FILE_EXPIRE_DAYS
        
        # Inicjalizacja B2 API
        self.info = InMemoryAccountInfo()
        self.b2_api = B2Api(self.info)
        self.bucket = None
        self._authorize()
    
    def _authorize(self):
        """Autoryzacja w Backblaze B2"""
        try:
            self.b2_api.authorize_account("production", self.key_id, self.app_key)
            self.bucket = self.b2_api.get_bucket_by_name(self.bucket_name)
            logger.info(f"Successfully authorized Backblaze B2 account and accessed bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to authorize Backblaze B2: {e}")
            raise
    
    def _generate_unique_filename(self, original_filename: str, sender_email: str) -> str:
        """
        Generuje unikalną nazwę pliku
        
        Args:
            original_filename: Oryginalna nazwa pliku
            sender_email: Email osoby udostępniającej
        
        Returns:
            Unikalna nazwa pliku z timestampem i hashem
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        email_hash = hashlib.md5(sender_email.encode()).hexdigest()[:8]
        
        # Rozdziel nazwę i rozszerzenie
        name, ext = os.path.splitext(original_filename)
        
        # Sanityzacja nazwy (usuń niebezpieczne znaki)
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        
        unique_name = f"{timestamp}_{email_hash}_{safe_name}{ext}"
        return unique_name
    
    def upload_file(
        self,
        file_data: bytes,
        original_filename: str,
        sender_email: str,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, str]:
        """
        Uploaduje plik do Backblaze B2
        
        Args:
            file_data: Dane pliku (bajty)
            original_filename: Oryginalna nazwa pliku
            sender_email: Email osoby udostępniającej
            content_type: Typ MIME pliku
        
        Returns:
            Dict z informacjami o pliku:
            - file_id: ID pliku w B2
            - file_name: Nazwa pliku w B2
            - download_url: Publiczny URL do pobrania
            - file_size: Rozmiar pliku w bajtach
            - upload_timestamp: Czas uploadu
        """
        try:
            # Generuj unikalną nazwę
            unique_filename = self._generate_unique_filename(original_filename, sender_email)
            
            # Przygotuj źródło danych
            upload_source = UploadSourceBytes(file_data)
            
            # Metadane pliku
            file_info = {
                'original_name': original_filename,
                'sender_email': sender_email,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(days=self.file_expire_days)).isoformat()
            }
            
            # Upload do B2
            file_version = self.bucket.upload(
                upload_source=upload_source,
                file_name=unique_filename,
                content_type=content_type,
                file_info=file_info
            )
            
            # Publiczny URL (bucket jest publiczny)
            download_url = f"{self.download_url}/{unique_filename}"
            
            logger.info(f"File uploaded successfully: {unique_filename} ({len(file_data)} bytes)")
            
            return {
                'file_id': file_version.id_,
                'file_name': unique_filename,
                'original_name': original_filename,
                'download_url': download_url,
                'file_size': len(file_data),
                'upload_timestamp': datetime.utcnow().isoformat(),
                'expires_at': file_info['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file to Backblaze B2: {e}")
            raise
    
    def delete_file(self, file_name: str, file_id: str) -> bool:
        """
        Usuwa plik z Backblaze B2
        
        Args:
            file_name: Nazwa pliku
            file_id: ID pliku w B2
        
        Returns:
            True jeśli usunięto pomyślnie
        """
        try:
            self.b2_api.delete_file_version(file_id, file_name)
            logger.info(f"File deleted successfully: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file from Backblaze B2: {e}")
            return False
    
    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """
        Pobiera informacje o pliku
        
        Args:
            file_id: ID pliku w B2
        
        Returns:
            Dict z informacjami o pliku lub None
        """
        try:
            file_version = self.b2_api.get_file_info(file_id)
            return {
                'file_id': file_version.id_,
                'file_name': file_version.file_name,
                'size': file_version.size,
                'content_type': file_version.content_type,
                'upload_timestamp': file_version.upload_timestamp
            }
        except Exception as e:
            logger.error(f"Failed to get file info from Backblaze B2: {e}")
            return None


# Singleton instance
_backblaze_service = None


def get_backblaze_service() -> BackblazeService:
    """Zwraca singleton instance BackblazeService"""
    global _backblaze_service
    if _backblaze_service is None:
        _backblaze_service = BackblazeService()
    return _backblaze_service
