"""
SQLAlchemy ORM Models dla CallCryptor Recordings
Schema: s07_callcryptor

Osobny plik dla ORM modeli (recordings_models.py ma Pydantic modele)
"""
from sqlalchemy import Column, String, Integer, BigInteger, Text, Boolean, TIMESTAMP, ForeignKey, JSON, Float
from datetime import datetime

from .database import Base


# =============================================================================
# MODEL: RecordingSource
# =============================================================================

class RecordingSource(Base):
    """
    Model źródła nagrań (folder lokalny lub konto email)
    """
    __tablename__ = 'recording_sources'
    __table_args__ = {'schema': 's07_callcryptor'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    
    # Core fields
    source_name = Column(Text, nullable=False)
    source_type = Column(String(20), nullable=False)  # 'folder' or 'email'
    
    # Folder options
    folder_path = Column(Text, nullable=True)
    file_extensions = Column(JSON, nullable=True)  # Lista: [".mp3", ".wav"]
    scan_depth = Column(Integer, default=1)
    
    # Email options
    email_account_id = Column(String, nullable=True)
    search_phrase = Column(Text, nullable=True)
    search_type = Column(String(20), default='SUBJECT')  # SUBJECT/ALL/BODY
    search_all_folders = Column(Boolean, default=False)
    target_folder = Column(String(100), default='INBOX')
    attachment_pattern = Column(Text, nullable=True)
    contact_ignore_words = Column(Text, nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    last_scan_at = Column(TIMESTAMP, nullable=True)
    recordings_count = Column(Integer, default=0)
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    # REMOVED: synced_at - PostgreSQL doesn't have this field
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<RecordingSource(id={self.id}, name={self.source_name}, type={self.source_type})>"


# =============================================================================
# MODEL: Recording
# =============================================================================

class Recording(Base):
    """
    Model nagrania (metadane - BEZ plików audio!)
    """
    __tablename__ = 'recordings'
    __table_args__ = {'schema': 's07_callcryptor'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    source_id = Column(String, ForeignKey('s07_callcryptor.recording_sources.id', ondelete='CASCADE'), nullable=False)
    
    # File info (NIE synchronizujemy file_path!)
    file_name = Column(Text, nullable=False)
    file_size = Column(BigInteger, nullable=True)
    file_hash = Column(String(64), nullable=True)  # MD5/SHA256
    
    # Email info (jeśli applicable)
    email_message_id = Column(Text, nullable=True)
    email_subject = Column(Text, nullable=True)
    email_sender = Column(Text, nullable=True)
    
    # Recording metadata
    contact_name = Column(Text, nullable=True)
    contact_phone = Column(String(50), nullable=True)
    recording_date = Column(TIMESTAMP, nullable=True)
    duration = Column(Integer, nullable=True)  # FIXED: duration not duration_seconds (PostgreSQL schema)
    
    # Tags and notes
    tags = Column(JSON, nullable=True)  # Lista stringów: ["important", "work"]
    notes = Column(Text, nullable=True)
    
    # Transcription (DODANE - brakujące pola)
    transcription_status = Column(String(20), default='pending', nullable=True)  # pending, processing, completed, failed
    transcription_text = Column(Text, nullable=True)  # Alias dla ai_transcript
    transcription_language = Column(String(10), nullable=True)  # Alias dla ai_language
    transcription_confidence = Column(Float, nullable=True)  # 0.0 - 1.0
    transcription_date = Column(TIMESTAMP, nullable=True)
    transcription_error = Column(Text, nullable=True)
    
    # AI analysis (opcjonalne)
    # REMOVED: ai_transcript - PostgreSQL doesn't have this field, only transcription_text and ai_summary_text
    ai_summary_text = Column(Text, nullable=True)  # FIXED: PostgreSQL uses ai_summary_text not ai_summary
    ai_summary_status = Column(String(20), default='pending', nullable=True)  # DODANE
    ai_summary_date = Column(TIMESTAMP, nullable=True)  # DODANE
    ai_summary_error = Column(Text, nullable=True)  # DODANE
    ai_summary_tasks = Column(JSON, nullable=True)  # Lista stringów (changed from List[Dict])
    ai_key_points = Column(JSON, nullable=True)  # Lista stringów
    ai_action_items = Column(JSON, nullable=True)  # Lista stringów
    # REMOVED: ai_sentiment, ai_language - PostgreSQL doesn't have these fields
    
    # Archivization (DODANE - brakujące pola)
    is_archived = Column(Boolean, default=False, nullable=True)
    archived_at = Column(TIMESTAMP, nullable=True)
    archive_reason = Column(Text, nullable=True)
    
    # Favorites (DODANE - brakujące pola)
    is_favorite = Column(Boolean, default=False, nullable=True)
    favorited_at = Column(TIMESTAMP, nullable=True)
    
    # Opcjonalne powiązania z innymi modułami
    task_id = Column(String, nullable=True)  # Link do Tasks
    # REMOVED: pomodoro_session_id - PostgreSQL doesn't have this field (only task_id and note_id)
    note_id = Column(String, nullable=True)  # Link do Notes
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    # REMOVED: synced_at - PostgreSQL doesn't have this field
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<Recording(id={self.id}, name={self.file_name}, contact={self.contact_name})>"


# =============================================================================
# MODEL: RecordingTag
# =============================================================================

class RecordingTag(Base):
    """
    Model tagu dla nagrań (zarządzanie wszystkimi używanymi tagami)
    """
    __tablename__ = 'recording_tags'
    __table_args__ = {'schema': 's07_callcryptor'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    
    # Core fields
    tag_name = Column(Text, nullable=False)
    tag_color = Column(Text, default='#2196F3')
    tag_icon = Column(Text, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    # REMOVED: synced_at - PostgreSQL doesn't have this field
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<RecordingTag(id={self.id}, name={self.tag_name})>"
