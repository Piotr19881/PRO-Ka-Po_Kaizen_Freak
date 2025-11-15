"""
Pydantic Schemas for TeamWork Module
Schematy walidacji danych dla API modułu TeamWork
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


# ============================================================================
# WORK GROUPS SCHEMAS
# ============================================================================

class WorkGroupBase(BaseModel):
    """Bazowy schemat grupy roboczej"""
    group_name: str = Field(..., min_length=1, max_length=200, description="Nazwa grupy")
    description: Optional[str] = Field(None, description="Opis grupy")


class WorkGroupCreate(WorkGroupBase):
    """Schemat tworzenia nowej grupy"""
    pass


class WorkGroupUpdate(BaseModel):
    """Schemat aktualizacji grupy"""
    group_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class GroupMemberInfo(BaseModel):
    """Informacje o członku grupy"""
    user_id: str
    role: str
    joined_at: datetime
    # Opcjonalne dane użytkownika (można rozszerzyć)
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class WorkGroupResponse(WorkGroupBase):
    """Schemat odpowiedzi z danymi grupy"""
    group_id: int
    created_by: str
    created_at: datetime
    is_active: bool
    members: Optional[List[GroupMemberInfo]] = []
    topics: Optional[List['TopicResponse']] = []
    
    class Config:
        from_attributes = True


# ============================================================================
# GROUP MEMBERS SCHEMAS
# ============================================================================

class GroupMemberAdd(BaseModel):
    """Schemat dodawania członka do grupy"""
    user_id: str = Field(..., description="ID użytkownika do dodania")
    role: str = Field(default='member', pattern='^(owner|member)$', description="Rola w grupie")


class GroupMemberUpdateRole(BaseModel):
    """Schemat zmiany roli członka"""
    role: str = Field(..., pattern='^(owner|member)$', description="Nowa rola")


class TransferOwnershipRequest(BaseModel):
    """Schemat żądania przekazania własności grupy"""
    new_owner_id: str = Field(..., description="ID nowego właściciela (musi być członkiem grupy)")


# ============================================================================
# TOPICS SCHEMAS
# ============================================================================

class TopicBase(BaseModel):
    """Bazowy schemat wątku"""
    topic_name: str = Field(..., min_length=1, max_length=300, description="Nazwa wątku")


class TopicCreate(TopicBase):
    """Schemat tworzenia nowego wątku"""
    group_id: int = Field(..., description="ID grupy, do której należy wątek")
    initial_message: Optional[str] = Field(None, description="Opcjonalna pierwsza wiadomość")


class TopicUpdate(BaseModel):
    """Schemat aktualizacji wątku"""
    topic_name: Optional[str] = Field(None, min_length=1, max_length=300)
    is_active: Optional[bool] = None


class TopicResponse(TopicBase):
    """Schemat odpowiedzi z danymi wątku"""
    topic_id: int
    group_id: int
    created_by: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# ============================================================================
# MESSAGES SCHEMAS
# ============================================================================

class MessageBase(BaseModel):
    """Bazowy schemat wiadomości"""
    content: str = Field(..., min_length=1, description="Treść wiadomości")
    background_color: Optional[str] = Field('#FFFFFF', pattern='^#[0-9A-Fa-f]{6}$', description="Kolor tła (hex)")
    is_important: bool = Field(False, description="Czy wiadomość jest oznaczona jako ważna")


class MessageCreate(MessageBase):
    """Schemat tworzenia nowej wiadomości"""
    topic_id: int = Field(..., description="ID wątku")


class MessageUpdate(BaseModel):
    """Schemat aktualizacji wiadomości"""
    content: Optional[str] = Field(None, min_length=1)
    background_color: Optional[str] = Field(None, pattern='^#[0-9A-Fa-f]{6}$')
    is_important: Optional[bool] = None


class MessageResponse(MessageBase):
    """Schemat odpowiedzi z danymi wiadomości"""
    message_id: int
    topic_id: int
    user_id: str
    created_at: datetime
    edited_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# TASKS SCHEMAS
# ============================================================================

class TaskBase(BaseModel):
    """Bazowy schemat zadania"""
    task_subject: str = Field(..., min_length=1, max_length=500, description="Temat zadania")
    task_description: Optional[str] = Field(None, description="Opis zadania")
    assigned_to: Optional[str] = Field(None, description="ID użytkownika, do którego przypisano zadanie")
    due_date: Optional[date] = Field(None, description="Termin wykonania")
    is_important: bool = Field(False, description="Czy zadanie jest ważne")


class TaskCreate(TaskBase):
    """Schemat tworzenia nowego zadania"""
    topic_id: int = Field(..., description="ID wątku")


class TaskUpdate(BaseModel):
    """Schemat aktualizacji zadania"""
    task_subject: Optional[str] = Field(None, min_length=1, max_length=500)
    task_description: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    is_important: Optional[bool] = None


class TaskCompleteRequest(BaseModel):
    """Schemat żądania oznaczenia zadania jako ukończone"""
    completed: bool = Field(..., description="Czy zadanie jest ukończone")


class TaskResponse(TaskBase):
    """Schemat odpowiedzi z danymi zadania"""
    task_id: int
    topic_id: int
    created_by: str
    created_at: datetime
    completed: bool
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# TOPIC FILES SCHEMAS (Backblaze B2 Integration)
# ============================================================================

class TopicFileBase(BaseModel):
    """Bazowy schemat pliku w wątku"""
    file_name: str = Field(..., description="Oryginalna nazwa pliku")
    is_important: bool = Field(False, description="Czy plik jest ważny")


class TopicFileUploadRequest(BaseModel):
    """Schemat żądania uploadu pliku (metadane)"""
    topic_id: int = Field(..., description="ID wątku")
    is_important: bool = Field(False, description="Czy plik jest ważny")


class TopicFileResponse(TopicFileBase):
    """Schemat odpowiedzi z danymi pliku"""
    file_id: int
    topic_id: int
    file_size: int
    content_type: Optional[str] = None
    b2_file_id: str
    b2_file_name: str
    download_url: str
    uploaded_by: str
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class TopicFileUpdate(BaseModel):
    """Schemat aktualizacji metadanych pliku"""
    is_important: Optional[bool] = None


# Forward reference resolution
WorkGroupResponse.model_rebuild()
