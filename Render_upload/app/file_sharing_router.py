"""
File Sharing Router for PRO-Ka-Po API
Endpoint do udostępniania plików przez Backblaze B2
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from loguru import logger

from .backblaze_service import get_backblaze_service
from .email_service import get_email_service

router = APIRouter(prefix="/api/v1/share", tags=["File Sharing"])


# =============================================================================
# PYDANTIC MODELS (Request/Response schemas)
# =============================================================================

class ShareFileResponse(BaseModel):
    """Schemat odpowiedzi udostępniania pliku"""
    success: bool
    message: str
    file_info: Optional[dict] = None


# =============================================================================
# FILE SHARING ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=ShareFileResponse, status_code=status.HTTP_201_CREATED)
async def share_file(
    file: UploadFile = File(..., description="Plik do udostępnienia"),
    recipient_email: EmailStr = Form(..., description="Adres email odbiorcy"),
    sender_email: EmailStr = Form(..., description="Adres email nadawcy"),
    sender_name: str = Form(..., description="Imię/nazwa nadawcy"),
    language: Optional[str] = Form(default="pl", description="Język emaila (pl/en/de)")
):
    """
    Udostępnia plik przez upload do Backblaze B2 i wysłanie emaila z linkiem
    
    Flow:
    1. Odbiera plik z aplikacji desktopowej
    2. Uploaduje plik do Backblaze B2
    3. Generuje publiczny link do pobrania
    4. Wysyła email z linkiem do odbiorcy
    
    Args:
        file: Plik do przesłania (multipart/form-data)
        recipient_email: Email odbiorcy
        sender_email: Email nadawcy (dla identyfikacji)
        sender_name: Imię nadawcy (wyświetlane w emailu)
        language: Język emaila (pl/en/de)
    
    Returns:
        ShareFileResponse z informacjami o pliku i statusem wysłania
    
    Raises:
        HTTPException: W przypadku błędu uploadu lub wysyłki emaila
    """
    try:
        # Walidacja języka
        if language not in ['pl', 'en', 'de']:
            language = 'pl'
        
        # Walidacja typu pliku (opcjonalne ograniczenia)
        max_file_size = 100 * 1024 * 1024  # 100 MB limit
        
        # Odczytaj plik do pamięci
        file_data = await file.read()
        file_size = len(file_data)
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        if file_size > max_file_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {max_file_size // (1024*1024)} MB"
            )
        
        logger.info(f"Received file: {file.filename} ({file_size} bytes) from {sender_email} to {recipient_email}")
        
        # Upload do Backblaze B2
        b2_service = get_backblaze_service()
        upload_result = b2_service.upload_file(
            file_data=file_data,
            original_filename=file.filename or "unnamed_file",
            sender_email=sender_email,
            content_type=file.content_type or "application/octet-stream"
        )
        
        logger.info(f"File uploaded to B2: {upload_result['file_name']}")
        
        # Wyślij email z linkiem
        email_service = get_email_service()
        email_sent = email_service.send_file_share_email(
            to_email=recipient_email,
            sender_name=sender_name,
            file_name=upload_result['original_name'],
            download_url=upload_result['download_url'],
            file_size=upload_result['file_size'],
            expires_at=upload_result['expires_at'],
            language=language
        )
        
        if not email_sent:
            # Plik został uploadowany, ale email się nie wysłał
            # Można rozważyć rollback (usunięcie pliku z B2)
            logger.warning(f"File uploaded but email failed to send to {recipient_email}")
            return ShareFileResponse(
                success=False,
                message="File uploaded but email notification failed",
                file_info=upload_result
            )
        
        logger.info(f"Email sent successfully to {recipient_email}")
        
        return ShareFileResponse(
            success=True,
            message=f"File shared successfully with {recipient_email}",
            file_info={
                'file_name': upload_result['original_name'],
                'file_size': upload_result['file_size'],
                'download_url': upload_result['download_url'],
                'expires_at': upload_result['expires_at']
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share file: {str(e)}"
        )


@router.get("/test", tags=["File Sharing"])
async def test_file_sharing():
    """Test endpoint dla sprawdzenia konfiguracji B2 i email"""
    try:
        b2_service = get_backblaze_service()
        email_service = get_email_service()
        
        return {
            "status": "ok",
            "b2_connected": True,
            "email_configured": bool(email_service.smtp_username),
            "bucket_name": b2_service.bucket_name
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
