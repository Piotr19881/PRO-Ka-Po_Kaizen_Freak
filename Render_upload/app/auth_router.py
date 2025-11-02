"""
Authentication Router for PRO-Ka-Po API
Endpointy do rejestracji, logowania, weryfikacji emaila, resetowania hasła
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from .database import get_db, User, UserProfile, VerificationToken
from .auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    create_refresh_token,
    decode_token,
    verify_token_type,
    generate_user_id
)
from .email_service import get_email_service
from .config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# =============================================================================
# PYDANTIC MODELS (Request/Response schemas)
# =============================================================================

class RegisterRequest(BaseModel):
    """Schemat żądania rejestracji"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Hasło musi mieć min. 8 znaków")
    name: str = Field(..., min_length=2, max_length=100)
    language: Optional[str] = Field(default="pl", pattern="^(pl|en|de)$")
    timezone: Optional[str] = Field(default="Europe/Warsaw")
    phone: Optional[str] = None


class RegisterResponse(BaseModel):
    """Schemat odpowiedzi rejestracji"""
    success: bool
    message: str
    user_id: str
    email: str


class VerifyEmailRequest(BaseModel):
    """Schemat żądania weryfikacji emaila"""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")


class VerifyEmailResponse(BaseModel):
    """Schemat odpowiedzi weryfikacji emaila"""
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "bearer"


class LoginRequest(BaseModel):
    """Schemat żądania logowania"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schemat odpowiedzi logowania"""
    success: bool
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class ForgotPasswordRequest(BaseModel):
    """Schemat żądania resetowania hasła"""
    email: EmailStr
    language: Optional[str] = Field(default="pl", pattern="^(pl|en|de)$")


class ForgotPasswordResponse(BaseModel):
    """Schemat odpowiedzi resetowania hasła"""
    success: bool
    message: str


class ResetPasswordRequest(BaseModel):
    """Schemat żądania ustawienia nowego hasła"""
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")
    new_password: str = Field(..., min_length=8)


class ResetPasswordResponse(BaseModel):
    """Schemat odpowiedzi ustawienia nowego hasła"""
    success: bool
    message: str


class RefreshTokenRequest(BaseModel):
    """Schemat żądania odświeżenia tokenu"""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Schemat odpowiedzi odświeżenia tokenu"""
    success: bool
    access_token: str
    token_type: str = "bearer"


# =============================================================================
# AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Rejestracja nowego użytkownika
    
    1. Sprawdza czy email już istnieje
    2. Tworzy użytkownika z zahashowanym hasłem
    3. Generuje kod weryfikacyjny
    4. Wysyła email z kodem
    
    Returns:
        RegisterResponse z ID użytkownika i informacją o wysłaniu emaila
    """
    try:
        # Sprawdź czy użytkownik już istnieje
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Utwórz nowego użytkownika
        user_id = generate_user_id()
        hashed_pwd = hash_password(request.password)
        
        new_user = User(
            id=user_id,
            email=request.email,
            password=hashed_pwd,
            name=request.name,
            language=request.language or "pl",
            timezone=request.timezone or "Europe/Warsaw",
            phone=request.phone,
            theme="light",
            email_verified=None  # Nie zweryfikowany
        )
        
        db.add(new_user)
        
        # Utwórz pusty profil użytkownika
        user_profile = UserProfile(
            user_id=user_id,
            preferences={}
        )
        db.add(user_profile)
        
        # Generuj kod weryfikacyjny
        email_service = get_email_service()
        verification_code = email_service.generate_verification_code()
        
        # Zapisz token weryfikacyjny
        expires_at = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        verification_token = VerificationToken(
            identifier=request.email,
            token=verification_code,
            expires=expires_at
        )
        db.add(verification_token)
        
        db.commit()
        
        # Wyślij email weryfikacyjny
        email_service.send_verification_email(
            to_email=request.email,
            user_name=request.name,
            verification_code=verification_code,
            language=request.language or "pl"
        )
        
        logger.info(f"New user registered: {request.email} (ID: {user_id})")
        
        return RegisterResponse(
            success=True,
            message="Registration successful. Please check your email for verification code.",
            user_id=user_id,
            email=request.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Weryfikacja emaila za pomocą kodu
    
    1. Sprawdza czy kod jest prawidłowy i nie wygasł
    2. Oznacza email jako zweryfikowany
    3. Zwraca tokeny JWT dla zalogowania
    
    Returns:
        VerifyEmailResponse z tokenami dostępu
    """
    try:
        # Znajdź token weryfikacyjny
        token = db.query(VerificationToken).filter(
            VerificationToken.identifier == request.email,
            VerificationToken.token == request.code
        ).first()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        # Sprawdź czy token nie wygasł
        if token.expires < datetime.utcnow():
            db.delete(token)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code expired. Please request a new one."
            )
        
        # Znajdź użytkownika
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Oznacz email jako zweryfikowany
        user.email_verified = datetime.utcnow()
        
        # Usuń zużyty token
        db.delete(token)
        db.commit()
        
        # Wygeneruj tokeny JWT
        access_token = create_access_token(data={"sub": user.id, "email": user.email})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        logger.info(f"Email verified for user: {user.email}")
        
        return VerifyEmailResponse(
            success=True,
            message="Email verified successfully",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Logowanie użytkownika
    
    1. Weryfikuje email i hasło
    2. Sprawdza czy email jest zweryfikowany
    3. Zwraca tokeny JWT
    
    Returns:
        LoginResponse z tokenami i danymi użytkownika
    """
    try:
        # Znajdź użytkownika
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Weryfikuj hasło
        if not verify_password(request.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Sprawdź czy email jest zweryfikowany
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email first."
            )
        
        # Wygeneruj tokeny
        access_token = create_access_token(data={"sub": user.id, "email": user.email})
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        # Przygotuj dane użytkownika (bez hasła!)
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "language": user.language,
            "timezone": user.timezone,
            "theme": user.theme
        }
        
        logger.info(f"User logged in: {user.email}")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Wysyła kod resetowania hasła na email
    
    1. Sprawdza czy użytkownik istnieje
    2. Generuje kod resetowania
    3. Wysyła email z kodem
    
    Returns:
        ForgotPasswordResponse z informacją o wysłaniu emaila
    """
    try:
        # Znajdź użytkownika
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Ze względów bezpieczeństwa, nie informuj że użytkownik nie istnieje
            return ForgotPasswordResponse(
                success=True,
                message="If this email exists, a reset code has been sent."
            )
        
        # Generuj kod resetowania
        email_service = get_email_service()
        reset_code = email_service.generate_verification_code()
        
        # Zapisz token resetowania
        expires_at = datetime.utcnow() + timedelta(minutes=settings.RESET_PASSWORD_CODE_EXPIRE_MINUTES)
        
        # Usuń stare tokeny resetowania dla tego użytkownika
        db.query(VerificationToken).filter(
            VerificationToken.identifier == f"reset_{request.email}"
        ).delete()
        
        reset_token = VerificationToken(
            identifier=f"reset_{request.email}",
            token=reset_code,
            expires=expires_at
        )
        db.add(reset_token)
        db.commit()
        
        # Wyślij email
        email_service.send_password_reset_email(
            to_email=request.email,
            user_name=user.name or "User",
            reset_code=reset_code,
            language=request.language or user.language or "pl"
        )
        
        logger.info(f"Password reset code sent to: {request.email}")
        
        return ForgotPasswordResponse(
            success=True,
            message="If this email exists, a reset code has been sent."
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Forgot password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send reset code"
        )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Resetuje hasło używając kodu z emaila
    
    1. Weryfikuje kod resetowania
    2. Ustawia nowe hasło
    3. Usuń token resetowania
    
    Returns:
        ResetPasswordResponse z informacją o powodzeniu
    """
    try:
        # Znajdź token resetowania
        token = db.query(VerificationToken).filter(
            VerificationToken.identifier == f"reset_{request.email}",
            VerificationToken.token == request.code
        ).first()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset code"
            )
        
        # Sprawdź czy token nie wygasł
        if token.expires < datetime.utcnow():
            db.delete(token)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset code expired. Please request a new one."
            )
        
        # Znajdź użytkownika
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Ustaw nowe hasło
        user.password = hash_password(request.new_password)
        user.updated_at = datetime.utcnow()
        
        # Usuń token resetowania
        db.delete(token)
        db.commit()
        
        logger.info(f"Password reset successful for user: {user.email}")
        
        return ResetPasswordResponse(
            success=True,
            message="Password reset successful. You can now log in with your new password."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Reset password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Odświeża access token używając refresh token
    
    Returns:
        RefreshTokenResponse z nowym access tokenem
    """
    try:
        # Dekoduj refresh token
        payload = decode_token(request.refresh_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Weryfikuj typ tokenu
        if not verify_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Pobierz user_id z tokenu
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Wygeneruj nowy access token
        new_access_token = create_access_token(data={"sub": user_id})
        
        logger.info(f"Access token refreshed for user: {user_id}")
        
        return RefreshTokenResponse(
            success=True,
            access_token=new_access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/resend-verification")
async def resend_verification(email: EmailStr, language: str = "pl", db: Session = Depends(get_db)):
    """
    Wysyła ponownie kod weryfikacyjny
    
    Args:
        email: Email użytkownika
        language: Język emaila (pl/en/de)
    
    Returns:
        Informacja o wysłaniu kodu
    """
    try:
        # Znajdź użytkownika
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Ze względów bezpieczeństwa, nie informuj że użytkownik nie istnieje
            return {"success": True, "message": "If this email exists, a verification code has been sent."}
        
        # Sprawdź czy email już zweryfikowany
        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Usuń stare tokeny weryfikacyjne
        db.query(VerificationToken).filter(
            VerificationToken.identifier == email
        ).delete()
        
        # Generuj nowy kod
        email_service = get_email_service()
        verification_code = email_service.generate_verification_code()
        
        # Zapisz token
        expires_at = datetime.utcnow() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES)
        verification_token = VerificationToken(
            identifier=email,
            token=verification_code,
            expires=expires_at
        )
        db.add(verification_token)
        db.commit()
        
        # Wyślij email
        email_service.send_verification_email(
            to_email=email,
            user_name=user.name or "User",
            verification_code=verification_code,
            language=language or user.language or "pl"
        )
        
        logger.info(f"Verification code resent to: {email}")
        
        return {"success": True, "message": "Verification code sent. Please check your email."}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code"
        )
