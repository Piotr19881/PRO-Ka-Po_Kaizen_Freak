"""
Main FastAPI Application for PRO-Ka-Po API
Główny plik aplikacji - endpoints i konfiguracja
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict
import uvicorn

from .config import settings
from .database import get_db, test_connection, init_db
from .auth_router import router as auth_router

# Inicjalizacja FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware - pozwala na zapytania z aplikacji desktopowej
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dodaj router autoryzacji
app.include_router(auth_router)


# =============================================================================
# HEALTH CHECK & STATUS ENDPOINTS
# =============================================================================

@app.get("/", tags=["Status"])
async def root() -> Dict[str, str]:
    """Root endpoint - informacje o API"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "status": "online",
        "description": settings.API_DESCRIPTION
    }


@app.get("/health", tags=["Status"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint - sprawdza stan aplikacji i połączenia z bazą"""
    db_status = "connected" if test_connection() else "disconnected"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "api_version": settings.API_VERSION
    }


@app.get("/api/test", tags=["Test"])
async def test_endpoint(db: Session = Depends(get_db)) -> Dict[str, str]:
    """Test endpoint - sprawdza połączenie z bazą danych"""
    try:
        from sqlalchemy import text
        # Próba wykonania prostego zapytania
        db.execute(text("SELECT 1"))
        return {
            "status": "success",
            "message": "Database connection successful",
            "database": settings.DATABASE_NAME
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# =============================================================================
# STARTUP & SHUTDOWN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Wykonywane przy starcie aplikacji"""
    print(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    print(f"Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    
    # Test połączenia z bazą
    if test_connection():
        print("✓ Database connection successful")
        # Inicjalizacja tabel (jeśli nie istnieją)
        init_db()
        print("✓ Database tables initialized")
    else:
        print("✗ Database connection failed!")


@app.on_event("shutdown")
async def shutdown_event():
    """Wykonywane przy zatrzymaniu aplikacji"""
    print(f"Shutting down {settings.API_TITLE}")


# =============================================================================
# PLACEHOLDER ENDPOINTS - DO IMPLEMENTACJI
# =============================================================================

@app.get("/api/v1/info", tags=["Info"])
async def api_info() -> Dict[str, str]:
    """Informacje o API"""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "description": settings.API_DESCRIPTION,
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "users": "/api/v1/users/*",
            "tasks": "/api/v1/tasks/*",
            "kanban": "/api/v1/kanban/*"
        }
    }


# =============================================================================
# MAIN - do uruchamiania lokalnie
# =============================================================================

if __name__ == "__main__":
    # Uruchomienie serwera (tylko dla testów lokalnych)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
