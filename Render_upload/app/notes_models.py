"""
SQLAlchemy Models dla Notes Module
Schema: s06_notes
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, TIMESTAMP, ForeignKey
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

from .database import Base


class Note(Base):
    """
    Model notatki w PostgreSQL.
    
    Przechowuje notatki z obsługą hierarchii (parent-child),
    formatowania HTML, i synchronizacji offline.
    """
    __tablename__ = 'notes'
    __table_args__ = {'schema': 's06_notes'}
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Foreign keys
    user_id = Column(
        String, 
        ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    parent_id = Column(
        String, 
        ForeignKey('s06_notes.notes.id', ondelete='CASCADE'), 
        nullable=True,
        index=True
    )
    
    # Data
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)  # HTML z formatowaniem
    color = Column(String(20), default='#1976D2')
    sort_order = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)
    
    # Timestamps & sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)  # Soft delete
    synced_at = Column(TIMESTAMP, nullable=True)   # Ostatnia synchronizacja
    version = Column(Integer, default=1, nullable=False)  # Conflict resolution
    
    def __repr__(self):
        return f"<Note(id={self.id}, title={self.title}, parent_id={self.parent_id})>"


class NoteLink(Base):
    """
    Model hiperłącza między notatkami.
    
    Umożliwia tworzenie linków z zaznaczonego tekstu do podnotatek.
    """
    __tablename__ = 'note_links'
    __table_args__ = {'schema': 's06_notes'}
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Foreign keys
    source_note_id = Column(
        String, 
        ForeignKey('s06_notes.notes.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    target_note_id = Column(
        String, 
        ForeignKey('s06_notes.notes.id', ondelete='CASCADE'), 
        nullable=False,
        index=True
    )
    
    # Link data
    link_text = Column(String(500), nullable=False)
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    
    # Sync metadata
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<NoteLink(id={self.id}, source={self.source_note_id}, target={self.target_note_id})>"


# =============================================================================
# PYDANTIC SCHEMAS (dla API validation)
# =============================================================================

class NoteCreate(BaseModel):
    """Schema dla tworzenia/sync notatki"""
    local_id: str
    user_id: str
    parent_id: Optional[str] = None
    title: str
    content: str = ""
    color: str = "#1976D2"
    version: int = 1
    synced_at: Optional[datetime] = None


class NoteUpdate(BaseModel):
    """Schema dla aktualizacji notatki"""
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None


class NoteResponse(BaseModel):
    """Schema dla odpowiedzi API z notatką"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    parent_id: Optional[str] = None
    title: str
    content: str
    color: str
    version: int
    synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class NoteLinkResponse(BaseModel):
    """Schema dla odpowiedzi API z linkiem"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    source_note_id: str
    target_note_id: str
    link_text: str
    start_position: int
    end_position: int
    created_at: datetime


# Dla kompatybilności z importami
NotesSchema = Note
NoteLinksSchema = NoteLink
