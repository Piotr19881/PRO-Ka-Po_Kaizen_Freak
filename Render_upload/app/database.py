"""
Database Module for PRO-Ka-Po API
Zarządzanie połączeniem z bazą danych PostgreSQL
"""
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, text, TIMESTAMP, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Generator

from .config import settings

# SQLAlchemy setup
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Sprawdza połączenie przed użyciem
    pool_recycle=3600,   # Odświeża połączenia co godzinę
    echo=False           # Ustaw True dla debugowania SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
metadata = MetaData(schema=settings.DATABASE_SCHEMA)


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Dependency do pobierania sesji bazy danych
    Używane w FastAPI endpoints
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicjalizacja bazy danych - tworzenie tabel
    Importuje modele i tworzy tabele jeśli nie istnieją
    """
    try:
        # Import wszystkich modeli aby SQLAlchemy je znało
        from . import alarms_models  # Schema s04_alarms_timers
        from . import pomodoro_models  # Schema s05_pomodoro
        
        # Tworzenie tabel dla wszystkich zarejestrowanych modeli
        Base.metadata.create_all(bind=engine)
        print("INFO: Database tables created/verified")
    except Exception as e:
        print(f"WARNING: init_db() error: {e}")
        print("INFO: Continuing with existing database structure")


def test_connection() -> bool:
    """
    Test połączenia z bazą danych
    
    Returns:
        True jeśli połączenie działa, False w przeciwnym razie
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False


# =============================================================================
# MODELE BAZY DANYCH - Schema: s01_user_accounts
# =============================================================================

class User(Base):
    """Model użytkownika - tabela users w schemacie s01_user_accounts"""
    __tablename__ = "users"
    __table_args__ = {'schema': settings.DATABASE_SCHEMA}
    
    id = Column(Text, primary_key=True, index=True)
    email = Column(Text, unique=True, index=True, nullable=False)
    password = Column(Text, nullable=False)  # hashed password
    name = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    timezone = Column(Text, default='Europe/Warsaw')
    language = Column(Text, default='pl')
    theme = Column(Text, default='light')
    email_verified = Column(TIMESTAMP, nullable=True)
    image = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserProfile(Base):
    """Model profilu użytkownika - tabela user_profiles w schemacie s01_user_accounts"""
    __tablename__ = "user_profiles"
    __table_args__ = {'schema': settings.DATABASE_SCHEMA}
    
    user_id = Column(Text, ForeignKey(f"{settings.DATABASE_SCHEMA}.users.id", ondelete="CASCADE"), primary_key=True)
    job_title = Column(Text, nullable=True)
    company = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)
    website = Column(Text, nullable=True)
    social_links = Column(JSON, nullable=True)
    preferences = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Account(Base):
    """Model konta zewnętrznego (OAuth) - tabela accounts w schemacie s01_user_accounts"""
    __tablename__ = "accounts"
    __table_args__ = {'schema': settings.DATABASE_SCHEMA}
    
    id = Column(Text, primary_key=True)
    user_id = Column(Text, ForeignKey(f"{settings.DATABASE_SCHEMA}.users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    provider_account_id = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    expires_at = Column(Integer, nullable=True)
    token_type = Column(Text, nullable=True)
    scope = Column(Text, nullable=True)
    id_token = Column(Text, nullable=True)
    session_state = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class Session(Base):
    """Model sesji użytkownika - tabela sessions w schemacie s01_user_accounts"""
    __tablename__ = "sessions"
    __table_args__ = {'schema': settings.DATABASE_SCHEMA}
    
    id = Column(Text, primary_key=True)
    session_token = Column(Text, unique=True, nullable=False)
    user_id = Column(Text, ForeignKey(f"{settings.DATABASE_SCHEMA}.users.id", ondelete="CASCADE"), nullable=False)
    expires = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class VerificationToken(Base):
    """Model tokenu weryfikacyjnego - tabela verification_tokens w schemacie s01_user_accounts"""
    __tablename__ = "verification_tokens"
    __table_args__ = {'schema': settings.DATABASE_SCHEMA}
    
    identifier = Column(Text, nullable=False)
    token = Column(Text, unique=True, nullable=False, primary_key=True)
    expires = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


# =============================================================================
# MODELE APLIKACYJNE - Schema: public (do przeniesienia później)
# =============================================================================


class Task(Base):
    """Model zadania"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="todo")  # todo, in_progress, done
    priority = Column(String(20), default="medium")  # low, medium, high
    category = Column(String(50), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class KanbanBoard(Base):
    """Model tablicy Kanban"""
    __tablename__ = "kanban_boards"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KanbanCard(Base):
    """Model karty na tablicy Kanban"""
    __tablename__ = "kanban_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("kanban_boards.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    column_name = Column(String(50), nullable=False)  # todo, in_progress, done
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
