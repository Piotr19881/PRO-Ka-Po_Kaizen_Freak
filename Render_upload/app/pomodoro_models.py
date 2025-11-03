"""
SQLAlchemy Models dla Pomodoro Module
Schema: s05_pomodoro
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Date, Text, ARRAY, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class SessionTopic(Base):
    """
    Model dla tabeli session_topics.
    
    Przechowuje predefiniowane tematy sesji Pomodoro,
    które użytkownik może przypisać do swoich sesji.
    """
    __tablename__ = 'session_topics'
    __table_args__ = (
        # PERFORMANCE: Indeksy dla częstych queries
        Index('idx_topics_user_deleted', 'user_id', 'deleted_at'),
        Index('idx_topics_local_id', 'user_id', 'local_id'),
        Index('idx_topics_updated', 'user_id', 'updated_at'),
        {'schema': 's05_pomodoro'}
    )
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Local ID from client (for sync)
    local_id = Column(String, nullable=False, unique=False, index=True)
    
    # Foreign key do users
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    
    # Dane tematu
    name = Column(String(100), nullable=False)
    color = Column(String(7), default='#FF6B6B', nullable=False)  # HEX color
    icon = Column(String(50), default='📚', nullable=True)
    description = Column(Text, nullable=True)
    
    # Statystyki (obliczane z logów)
    total_sessions = Column(Integer, default=0, nullable=False)
    total_work_time = Column(Integer, default=0, nullable=False)  # minuty
    total_break_time = Column(Integer, default=0, nullable=False)  # minuty
    
    # Kolejność i widoczność
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)
    
    # Timestamps & sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    version = Column(Integer, default=1, nullable=False)  # Conflict resolution
    
    # Relationships
    sessions = relationship("SessionLog", back_populates="topic", foreign_keys="SessionLog.topic_id")
    
    def __repr__(self):
        return f"<SessionTopic(id={self.id}, name={self.name}, user_id={self.user_id})>"


class SessionLog(Base):
    """
    Model dla tabeli session_logs.
    
    Przechowuje historię wykonanych sesji Pomodoro
    wraz z czasami, statusem i dodatkowymi metadanymi.
    """
    __tablename__ = 'session_logs'
    __table_args__ = (
        # PERFORMANCE: Indeksy dla częstych queries
        Index('idx_sessions_user_deleted', 'user_id', 'deleted_at'),
        Index('idx_sessions_local_id', 'user_id', 'local_id'),
        Index('idx_sessions_date', 'user_id', 'session_date'),
        Index('idx_sessions_updated', 'user_id', 'updated_at'),
        {'schema': 's05_pomodoro'}
    )
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Local ID from client (for sync)
    local_id = Column(String, nullable=False, unique=False, index=True)
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    topic_id = Column(String, ForeignKey('s05_pomodoro.session_topics.id', ondelete='SET NULL'), nullable=True)
    
    # Dane czasowe sesji
    session_date = Column(Date, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)  # Nullable jeśli przerwana
    
    # Czasy trwania (w minutach)
    work_duration = Column(Integer, nullable=False)
    short_break_duration = Column(Integer, nullable=True)
    long_break_duration = Column(Integer, nullable=True)
    actual_work_time = Column(Integer, nullable=True)  # Rzeczywisty czas
    actual_break_time = Column(Integer, nullable=True)
    
    # Status i typ sesji
    session_type = Column(String(20), default='work', nullable=False)  # 'work', 'short_break', 'long_break'
    status = Column(String(20), default='completed', nullable=False)  # 'completed', 'interrupted', 'skipped'
    pomodoro_count = Column(Integer, default=1, nullable=False)  # Który pomodoro w cyklu (1-4)
    
    # Dodatkowe dane
    notes = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True)  # Array tagów
    productivity_rating = Column(Integer, nullable=True)  # 1-5
    
    # Timestamps & sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    version = Column(Integer, default=1, nullable=False)  # Conflict resolution
    
    # Relationships
    topic = relationship("SessionTopic", back_populates="sessions", foreign_keys=[topic_id])
    
    def __repr__(self):
        return f"<SessionLog(id={self.id}, type={self.session_type}, status={self.status}, user_id={self.user_id})>"


# Dla kompatybilności z importami
PomodoroTopicSchema = SessionTopic
PomodoroSessionSchema = SessionLog
