"""
Authentication Utilities for PRO-Ka-Po API
Obsługa hashowania haseł, weryfikacji, i generowania tokenów JWT
"""
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from .config import settings

# Security scheme for FastAPI
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hashuje hasło używając bcrypt
    
    Args:
        password: Hasło w postaci zwykłego tekstu
        
    Returns:
        Zahashowane hasło jako string
    """
    try:
        # Generuj salt i hashuj hasło
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Weryfikuje czy podane hasło pasuje do zahashowanego
    
    Args:
        plain_password: Hasło w postaci zwykłego tekstu
        hashed_password: Zahashowane hasło z bazy danych
        
    Returns:
        True jeśli hasła pasują, False w przeciwnym razie
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Tworzy JWT access token
    
    Args:
        data: Dane do zakodowania w tokenie (np. user_id, email)
        expires_delta: Opcjonalny czas wygaśnięcia tokenu
        
    Returns:
        JWT token jako string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(data: dict) -> str:
    """
    Tworzy JWT refresh token (długoterminowy)
    
    Args:
        data: Dane do zakodowania w tokenie (np. user_id)
        
    Returns:
        JWT refresh token jako string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise


def decode_token(token: str) -> Optional[dict]:
    """
    Dekoduje i weryfikuje JWT token
    
    Args:
        token: JWT token do dekodowania
        
    Returns:
        Zdekodowane dane z tokenu lub None jeśli token jest nieprawidłowy
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return None


def verify_token_type(payload: dict, expected_type: str) -> bool:
    """
    Weryfikuje czy token jest odpowiedniego typu (access/refresh)
    
    Args:
        payload: Zdekodowany payload tokenu
        expected_type: Oczekiwany typ tokenu ('access' lub 'refresh')
        
    Returns:
        True jeśli typ się zgadza, False w przeciwnym razie
    """
    token_type = payload.get("type")
    if token_type != expected_type:
        logger.warning(f"Invalid token type. Expected {expected_type}, got {token_type}")
        return False
    return True


def generate_user_id() -> str:
    """
    Generuje unikalny ID użytkownika
    Używa UUID v4
    
    Returns:
        Unikalny ID jako string
    """
    import uuid
    return str(uuid.uuid4())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency - weryfikuje JWT token i zwraca dane użytkownika.
    
    Args:
        credentials: Bearer token z headera Authorization
        
    Returns:
        Dict z danymi użytkownika (user_id, email, etc.)
        
    Raises:
        HTTPException 401: Jeśli token jest nieprawidłowy lub wygasły
    """
    # DEV ONLY: Bypass dla testów lokalnych
    if credentials.credentials == "test-token-bypass":
        logger.warning("Using test bypass for authentication - DEV ONLY!")
        return {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "payload": {"sub": "test-user-123", "email": "test@example.com"}
        }
    
    token = credentials.credentials
    
    # Dekoduj token
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Sprawdź typ tokenu
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected access token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Sprawdź czy token nie wygasł
    exp = payload.get("exp")
    if exp is None or datetime.utcnow().timestamp() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Zwróć dane użytkownika
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "payload": payload
    }

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency do weryfikacji i pobierania aktualnego użytkownika z tokenu.
    
    Używane w FastAPI endpoints jako Depends(get_current_user).
    
    Args:
        credentials: HTTP Authorization Bearer token
        
    Returns:
        Dict z danymi użytkownika (user_id, email, etc.)
        
    Raises:
        HTTPException: Jeśli token jest nieprawidłowy lub wygasł
    """
    token = credentials.credentials
    
    # Dekoduj token
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Weryfikuj typ tokenu
    if not verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Sprawdź czy token nie wygasł
    exp = payload.get("exp")
    if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Zwróć dane użytkownika
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": user_id,
        "email": email,
        "payload": payload
    }
