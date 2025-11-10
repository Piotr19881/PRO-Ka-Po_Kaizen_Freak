"""
CallCryptor Recordings - Pydantic Models
=========================================

Models dla synchronizacji nagrań między klientem a serwerem.
Privacy-first: NIE synchronizujemy plików audio, tylko metadane.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================
# Recording Source Models
# ============================================================

class RecordingSourceBase(BaseModel):
    """Bazowy model źródła nagrań"""
    source_name: str = Field(..., min_length=1, max_length=200)
    source_type: str = Field(..., pattern="^(folder|email)$")
    
    # Folder options
    folder_path: Optional[str] = None
    file_extensions: Optional[List[str]] = Field(default_factory=lambda: [".mp3", ".wav", ".m4a"])
    scan_depth: int = Field(default=1, ge=1, le=10)
    
    # Email options
    email_account_id: Optional[str] = None
    search_phrase: Optional[str] = None
    search_type: str = Field(default="SUBJECT", pattern="^(SUBJECT|ALL|BODY)$")
    search_all_folders: bool = False
    target_folder: str = "INBOX"
    attachment_pattern: Optional[str] = None
    contact_ignore_words: Optional[str] = None
    
    # Metadata
    is_active: bool = True
    last_scan_at: Optional[datetime] = None
    recordings_count: int = 0
    
    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in ['folder', 'email']:
            raise ValueError('source_type must be "folder" or "email"')
        return v


class RecordingSourceCreate(RecordingSourceBase):
    """Model tworzenia źródła"""
    pass


class RecordingSourceUpdate(BaseModel):
    """Model aktualizacji źródła (wszystkie pola opcjonalne)"""
    source_name: Optional[str] = Field(None, min_length=1, max_length=200)
    is_active: Optional[bool] = None
    folder_path: Optional[str] = None
    file_extensions: Optional[List[str]] = None
    scan_depth: Optional[int] = Field(None, ge=1, le=10)
    email_account_id: Optional[str] = None
    search_phrase: Optional[str] = None
    search_type: Optional[str] = Field(None, pattern="^(SUBJECT|ALL|BODY)$")
    search_all_folders: Optional[bool] = None
    target_folder: Optional[str] = None
    attachment_pattern: Optional[str] = None
    contact_ignore_words: Optional[str] = None
    last_scan_at: Optional[datetime] = None
    recordings_count: Optional[int] = None


class RecordingSourceResponse(RecordingSourceBase):
    """Model odpowiedzi z źródłem"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    
    model_config = {"from_attributes": True}


# ============================================================
# Recording Models
# ============================================================

class RecordingBase(BaseModel):
    """Bazowy model nagrania - PRIVACY-FIRST: bez plików audio!"""
    # File metadata (NO file_path!)
    file_name: str = Field(..., min_length=1, max_length=500)
    file_size: Optional[int] = Field(None, ge=0)
    file_hash: Optional[str] = Field(None, max_length=64)
    
    # Email info
    email_message_id: Optional[str] = None
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None
    
    # Recording metadata
    contact_name: Optional[str] = Field(None, max_length=200)
    contact_phone: Optional[str] = Field(None, max_length=50)
    duration: Optional[int] = Field(None, ge=0)  # seconds
    recording_date: Optional[datetime] = None
    
    # Organization
    tags: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None
    
    # Transcription
    transcription_status: str = Field(default="pending", pattern="^(pending|processing|completed|failed)$")
    transcription_text: Optional[str] = None
    transcription_language: Optional[str] = None
    transcription_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    transcription_date: Optional[datetime] = None
    transcription_error: Optional[str] = None
    
    # AI Summary
    ai_summary_status: str = Field(default="pending", pattern="^(pending|processing|completed|failed)$")
    ai_summary_text: Optional[str] = None
    ai_summary_date: Optional[datetime] = None
    ai_summary_error: Optional[str] = None
    ai_summary_tasks: Optional[List[str]] = None  # Changed from List[Dict] - lista stringów z zadaniami
    ai_key_points: Optional[List[str]] = None
    ai_action_items: Optional[List[Dict[str, Any]]] = None  # Pozostaje Dict dla action items (mogą mieć deadline, assignee, etc)
    
    # Links to other modules
    note_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    
    # Flags
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    is_favorite: bool = False
    favorited_at: Optional[datetime] = None
    
    @field_validator('transcription_status', 'ai_summary_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = ['pending', 'processing', 'completed', 'failed']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v


class RecordingCreate(RecordingBase):
    """Model tworzenia nagrania"""
    source_id: UUID


class RecordingUpdate(BaseModel):
    """Model aktualizacji nagrania (wszystkie pola opcjonalne)"""
    file_name: Optional[str] = Field(None, min_length=1, max_length=500)
    file_size: Optional[int] = Field(None, ge=0)
    file_hash: Optional[str] = Field(None, max_length=64)
    email_message_id: Optional[str] = None
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None
    contact_name: Optional[str] = Field(None, max_length=200)
    contact_phone: Optional[str] = Field(None, max_length=50)
    duration: Optional[int] = Field(None, ge=0)
    recording_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    transcription_status: Optional[str] = Field(None, pattern="^(pending|processing|completed|failed)$")
    transcription_text: Optional[str] = None
    transcription_language: Optional[str] = None
    transcription_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    transcription_date: Optional[datetime] = None
    transcription_error: Optional[str] = None
    ai_summary_status: Optional[str] = Field(None, pattern="^(pending|processing|completed|failed)$")
    ai_summary_text: Optional[str] = None
    ai_summary_date: Optional[datetime] = None
    ai_summary_error: Optional[str] = None
    ai_summary_tasks: Optional[List[str]] = None  # Changed from List[Dict] - lista stringów z zadaniami
    ai_key_points: Optional[List[str]] = None
    ai_action_items: Optional[List[Dict[str, Any]]] = None
    note_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    is_archived: Optional[bool] = None
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    is_favorite: Optional[bool] = None
    favorited_at: Optional[datetime] = None


class RecordingResponse(RecordingBase):
    """Model odpowiedzi z nagraniem"""
    id: UUID
    user_id: UUID
    source_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    
    model_config = {"from_attributes": True}


# ============================================================
# Recording Tag Models
# ============================================================

class RecordingTagBase(BaseModel):
    """Bazowy model tagu"""
    tag_name: str = Field(..., min_length=1, max_length=100)
    tag_color: str = Field(default="#2196F3", pattern="^#[0-9A-Fa-f]{6}$")
    tag_icon: Optional[str] = None
    usage_count: int = Field(default=0, ge=0)
    
    @field_validator('tag_color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be in format #RRGGBB')
        return v.upper()


class RecordingTagCreate(RecordingTagBase):
    """Model tworzenia tagu"""
    pass


class RecordingTagUpdate(BaseModel):
    """Model aktualizacji tagu"""
    tag_name: Optional[str] = Field(None, min_length=1, max_length=100)
    tag_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    tag_icon: Optional[str] = None
    usage_count: Optional[int] = Field(None, ge=0)


class RecordingTagResponse(RecordingTagBase):
    """Model odpowiedzi z tagiem"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    
    model_config = {"from_attributes": True}


# ============================================================
# Bulk Sync Models
# ============================================================

class RecordingSyncItem(BaseModel):
    """Pojedyncze nagranie do synchronizacji - wszystkie pola z ORM"""
    id: str  # Changed from UUID to str
    source_id: str  # Changed from UUID to str
    file_name: str
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    
    # Email info
    email_message_id: Optional[str] = None
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None
    
    # Recording metadata
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    duration_seconds: Optional[int] = None  # Changed from duration
    recording_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    
    # Transcription (DODANE - brakujące pola)
    transcription_status: str = "pending"
    transcription_text: Optional[str] = None
    transcription_language: Optional[str] = None
    transcription_confidence: Optional[float] = None
    transcription_date: Optional[datetime] = None
    transcription_error: Optional[str] = None
    
    # AI analysis
    # REMOVED: ai_transcript - PostgreSQL doesn't have this field (only transcription_text and ai_summary_text)
    ai_summary: Optional[str] = None  # Changed from ai_summary_text
    ai_summary_status: str = "pending"  # DODANE
    ai_summary_date: Optional[datetime] = None  # DODANE
    ai_summary_error: Optional[str] = None  # DODANE
    ai_summary_tasks: Optional[List[str]] = None  # Changed from List[Dict]
    ai_key_points: Optional[List[str]] = None  # NEW
    ai_action_items: Optional[List[Dict[str, Any]]] = None  # Allow structured action items
    # REMOVED: ai_sentiment, ai_language - PostgreSQL doesn't have these fields
    
    # Archivization (DODANE - brakujące pola)
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    
    # Favorites (DODANE - brakujące pola)
    is_favorite: bool = False
    favorited_at: Optional[datetime] = None
    
    # Links to other modules
    note_id: Optional[str] = None  # Changed from UUID to str
    task_id: Optional[str] = None  # Changed from UUID to str
    # REMOVED: pomodoro_session_id - PostgreSQL doesn't have this field
    
    # Sync metadata
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    # REMOVED: synced_at - PostgreSQL doesn't have this field
    version: int


class BulkSyncRequest(BaseModel):
    """Request dla bulk synchronizacji"""
    recordings: List[RecordingSyncItem] = Field(..., max_length=100)
    sources: Optional[List[RecordingSourceResponse]] = Field(default_factory=list)
    tags: Optional[List[RecordingTagResponse]] = Field(default_factory=list)
    last_sync_at: Optional[datetime] = None
    
    @field_validator('recordings')
    @classmethod
    def validate_recordings_limit(cls, v: List[RecordingSyncItem]) -> List[RecordingSyncItem]:
        if len(v) > 100:
            raise ValueError('Cannot sync more than 100 recordings at once')
        return v


class BulkSyncResponse(BaseModel):
    """Response z bulk synchronizacji"""
    recordings_created: int = 0
    recordings_updated: int = 0
    recordings_deleted: int = 0
    sources_created: int = 0
    sources_updated: int = 0
    sources_deleted: int = 0
    tags_created: int = 0
    tags_updated: int = 0
    tags_deleted: int = 0
    conflicts_resolved: int = 0
    server_recordings: List[RecordingSyncItem] = Field(default_factory=list)
    server_sources: List[RecordingSourceResponse] = Field(default_factory=list)
    server_tags: List[RecordingTagResponse] = Field(default_factory=list)
    sync_timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Sync Stats Models
# ============================================================

class SyncStatsResponse(BaseModel):
    """Statystyki synchronizacji dla użytkownika"""
    total_recordings: int = 0
    total_sources: int = 0
    total_tags: int = 0
    last_sync_at: Optional[datetime] = None
    pending_uploads: int = 0
    pending_downloads: int = 0
