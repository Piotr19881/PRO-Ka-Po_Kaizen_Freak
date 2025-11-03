"""
SQLAlchemy Models dla Alarms & Timers
Schema: s04_alarms_timers
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ARRAY, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from .database import Base

# Użyj Base z database.py
# Base już jest zdefiniowany, więc używamy go


class AlarmTimer(Base):
    """
    Model dla unified table alarms_timers.
    
    Przechowuje zarówno alarmy jak i timery w jednej tabeli,
    rozróżniane przez pole 'type'.
    """
    __tablename__ = 'alarms_timers'
    __table_args__ = {'schema': 's04_alarms_timers'}
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Foreign key do users
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    
    # Type discriminator
    type = Column(String, nullable=False)  # 'alarm' lub 'timer'
    
    # Common fields
    label = Column(String(200), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Alarm specific fields
    alarm_time = Column(String(5), nullable=True)  # Format: HH:MM
    recurrence = Column(String(20), nullable=True)  # 'once', 'daily', 'weekly', 'weekdays', 'weekends'
    days = Column(ARRAY(Integer), nullable=True)   # [0,1,2,3,4,5,6]
    
    # Timer specific fields
    duration = Column(Integer, nullable=True)       # Sekundy
    remaining = Column(Integer, nullable=True)      # Pozostały czas
    repeat = Column(Boolean, nullable=True)         # Auto-restart
    started_at = Column(DateTime, nullable=True)    # Timestamp startu
    
    # Common settings
    play_sound = Column(Boolean, default=True, nullable=False)
    show_popup = Column(Boolean, default=True, nullable=False)
    custom_sound = Column(String, nullable=True)    # Ścieżka do pliku
    
    # Timestamps & sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)    # Soft delete
    synced_at = Column(DateTime, nullable=True)     # Ostatnia synchronizacja
    version = Column(Integer, default=1, nullable=False)  # Conflict resolution
    
    def __repr__(self):
        return f"<AlarmTimer(id={self.id}, type={self.type}, label={self.label})>"


# Dla kompatybilności z importami
AlarmsTimersSchema = AlarmTimer
