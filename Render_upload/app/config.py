"""
Configuration Module for PRO-Ka-Po API
Zarządzanie konfiguracją aplikacji z wykorzystaniem zmiennych środowiskowych
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Konfiguracja aplikacji"""
    
    # Database Configuration
    DATABASE_HOST: str = "dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "pro_ka_po"
    DATABASE_USER: str = "pro_ka_po_user"
    DATABASE_PASSWORD: str = "01pHONi8u23ZlHNffO64TcmWywetoiUD"
    DATABASE_SCHEMA: str = "s01_user_accounts"  # Schemat dla użytkowników
    
    # Security Configuration
    SECRET_KEY: str = "super-secret-key-change-this-in-production-use-random-string-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API Configuration
    API_TITLE: str = "PRO-Ka-Po API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "Secure API for PRO-Ka-Po Kaizen Freak Application"
    
    # CORS Configuration
    CORS_ORIGINS: str = "*"
    
    # Email Configuration (SMTP Gmail)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "PRO-Ka-Po Kaizen Freak"
    
    # Verification Settings
    VERIFICATION_CODE_LENGTH: int = 6
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 15
    RESET_PASSWORD_CODE_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_SUBJECT: str = "Kod weryfikacyjny - PRO-Ka-Po"
    EMAIL_RESET_PASSWORD_SUBJECT: str = "Reset hasła - PRO-Ka-Po"
    
    # Backblaze B2 Configuration (File Sharing)
    B2_APPLICATION_KEY_ID: str = ""
    B2_APPLICATION_KEY: str = ""
    B2_BUCKET_NAME: str = "pro-ka-po-files"
    B2_BUCKET_ID: str = ""
    B2_DOWNLOAD_URL: str = ""
    B2_FILE_EXPIRE_DAYS: int = 7  # Domyślnie pliki wygasają po 7 dniach
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    @property
    def DATABASE_URL(self) -> str:
        """Zwraca pełny URL do bazy danych"""
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        """Zwraca listę dozwolonych origins dla CORS"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Singleton instance
settings = Settings()
