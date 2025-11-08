"""
SQLAlchemy Models dla Habit Tracker
Schema: s07_habits
"""
from sqlalchemy import Column, String, Integer, Date, Text, ForeignKey, TIMESTAMP
from datetime import datetime

from .database import Base


# =============================================================================
# MODEL: HabitColumn
# =============================================================================

class HabitColumn(Base):
    """
    Model kolumny nawyku (definicja nawyku)
    """
    __tablename__ = 'habit_columns'
    __table_args__ = {'schema': 's07_habits'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    
    # Core fields
    name = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)  # checkbox, counter, duration, time, scale, text
    position = Column(Integer, default=0, nullable=False)
    scale_max = Column(Integer, default=10, nullable=False)
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<HabitColumn(id={self.id}, name={self.name}, type={self.type})>"


# =============================================================================
# MODEL: HabitRecord
# =============================================================================

class HabitRecord(Base):
    """
    Model rekordu nawyku (wartość dla konkretnej daty)
    """
    __tablename__ = 'habit_records'
    __table_args__ = {'schema': 's07_habits'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    habit_id = Column(String, ForeignKey('s07_habits.habit_columns.id', ondelete='CASCADE'), nullable=False)
    
    # Core fields
    date = Column(Date, nullable=False)
    value = Column(Text, nullable=True)  # Wartość może być pusta
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<HabitRecord(habit_id={self.habit_id}, date={self.date}, value={self.value})>"


# =============================================================================
# UWAGA: HabitSettings nie ma modelu SQLAlchemy
# Wszystkie ustawienia zapisywane tylko lokalnie w SQLite
# =============================================================================

# =============================================================================
# Dla kompatybilności
# =============================================================================
HabitsSchema = HabitColumn