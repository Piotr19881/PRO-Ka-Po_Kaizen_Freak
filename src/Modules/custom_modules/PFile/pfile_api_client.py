"""
PFile API Client Module
Client for communicating with Backblaze B2 file sharing API
"""
import requests
from typing import Optional, Dict, Any, Callable
from pathlib import Path
from loguru import logger


class PFileAPIClient:
    """Client for file sharing API (Backblaze B2)"""
    
    def __init__(self, base_url: str = "https://pro-ka-po-backend.onrender.com"):
        """
        Initialize API client
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
        self.upload_endpoint = f"{self.base_url}/api/v1/share/upload"
        self.test_endpoint = f"{self.base_url}/api/v1/share/test"
        self.timeout = 300  # 5 minutes timeout for large files
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test API connection and configuration
        
        Returns:
            Dict with status information
        """
        try:
            response = requests.get(self.test_endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def upload_file(
        self,
        file_path: str,
        recipient_email: str,
        sender_email: str,
        sender_name: str,
        language: str = 'pl',
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to Backblaze B2 and send share email
        
        Args:
            file_path: Path to file to upload
            recipient_email: Recipient's email address
            sender_email: Sender's email address
            sender_name: Sender's name (displayed in email)
            language: Email language (pl/en/de)
            progress_callback: Optional callback(bytes_sent, total_bytes)
        
        Returns:
            Dict with result:
            {
                'success': bool,
                'message': str,
                'file_info': {
                    'file_name': str,
                    'file_size': int,
                    'download_url': str,
                    'expires_at': str
                }
            }
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large or email invalid
            Exception: On upload failure
        """
        file_path_obj = Path(file_path)
        
        # Validate file exists
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Validate file size (100 MB limit)
        file_size = file_path_obj.stat().st_size
        max_size = 100 * 1024 * 1024  # 100 MB
        
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size / (1024*1024):.1f} MB. Maximum: 100 MB")
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        # Validate emails
        if not recipient_email or '@' not in recipient_email:
            raise ValueError("Invalid recipient email")
        
        if not sender_email or '@' not in sender_email:
            raise ValueError("Invalid sender email")
        
        # Validate language
        if language not in ['pl', 'en', 'de']:
            language = 'pl'
        
        logger.info(f"Uploading file: {file_path_obj.name} ({file_size} bytes)")
        
        try:
            # Prepare multipart form data
            with open(file_path, 'rb') as file:
                files = {
                    'file': (file_path_obj.name, file, 'application/octet-stream')
                }
                
                data = {
                    'recipient_email': recipient_email,
                    'sender_email': sender_email,
                    'sender_name': sender_name,
                    'language': language
                }
                
                # Upload with progress tracking
                if progress_callback:
                    # TODO: Implement progress tracking with requests_toolbelt
                    # For now, just upload without progress
                    pass
                
                response = requests.post(
                    self.upload_endpoint,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"File uploaded successfully: {file_path_obj.name}")
                
                return result
        
        except requests.exceptions.Timeout:
            logger.error("Upload timeout - file too large or slow connection")
            raise Exception("Upload timeout. Please try again or use a smaller file.")
        
        except requests.exceptions.ConnectionError:
            logger.error("Connection error - cannot reach API server")
            raise Exception("Cannot connect to server. Check your internet connection.")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during upload: {e}")
            error_message = "Upload failed"
            
            try:
                error_data = e.response.json()
                error_message = error_data.get('detail', error_message)
            except:
                pass
            
            raise Exception(f"Upload failed: {error_message}")
        
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise Exception(f"Upload failed: {str(e)}")
    
    def upload_file_with_retry(
        self,
        file_path: str,
        recipient_email: str,
        sender_email: str,
        sender_name: str,
        language: str = 'pl',
        max_retries: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Upload file with retry logic
        
        Args:
            Same as upload_file()
            max_retries: Maximum number of retry attempts
        
        Returns:
            Same as upload_file()
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Upload attempt {attempt + 1}/{max_retries}")
                return self.upload_file(
                    file_path=file_path,
                    recipient_email=recipient_email,
                    sender_email=sender_email,
                    sender_name=sender_name,
                    language=language,
                    progress_callback=progress_callback
                )
            except Exception as e:
                last_exception = e
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # All retries failed
        raise Exception(f"Upload failed after {max_retries} attempts: {last_exception}")
    
    def share_file(
        self,
        file_path: str,
        expires_in_hours: int = 24
    ) -> Optional[str]:
        """
        Quick share file - upload and get direct download link
        No email notification, just returns the URL
        
        Args:
            file_path: Path to file to upload
            expires_in_hours: Link expiration time in hours (default 24)
        
        Returns:
            Download URL string or None on failure
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is too large
            Exception: On upload failure
        """
        file_path_obj = Path(file_path)
        
        # Validate file exists
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Validate file size (100 MB limit)
        file_size = file_path_obj.stat().st_size
        max_size = 100 * 1024 * 1024  # 100 MB
        
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size / (1024*1024):.1f} MB. Maximum: 100 MB")
        
        if file_size == 0:
            raise ValueError("File is empty")
        
        logger.info(f"Quick sharing file: {file_path_obj.name} ({file_size} bytes)")
        
        try:
            # Prepare multipart form data
            with open(file_path, 'rb') as file:
                files = {
                    'file': (file_path_obj.name, file, 'application/octet-stream')
                }
                
                data = {
                    'expires_in_hours': expires_in_hours,
                    'quick_share': True  # Flag for API to skip email
                }
                
                # Use quick share endpoint
                quick_share_endpoint = f"{self.base_url}/api/v1/share/quick"
                
                response = requests.post(
                    quick_share_endpoint,
                    files=files,
                    data=data,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract download URL from response
                if result.get('success'):
                    download_url = result.get('file_info', {}).get('download_url')
                    logger.info(f"File shared successfully: {download_url}")
                    return download_url
                else:
                    logger.error(f"Share failed: {result.get('message')}")
                    return None
        
        except requests.exceptions.Timeout:
            logger.error("Share timeout - file too large or slow connection")
            raise Exception("Upload timeout. Please try again or use a smaller file.")
        
        except requests.exceptions.ConnectionError:
            logger.error("Connection error - cannot reach API server")
            raise Exception("Cannot connect to server. Check your internet connection.")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during share: {e}")
            error_message = "Share failed"
            
            try:
                error_data = e.response.json()
                error_message = error_data.get('detail', error_message)
            except:
                pass
            
            raise Exception(f"Share failed: {error_message}")
        
        except Exception as e:
            logger.error(f"Unexpected error during share: {e}")
            raise Exception(f"Share failed: {str(e)}")
