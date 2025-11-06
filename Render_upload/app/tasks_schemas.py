"""
Pydantic Schemas dla Tasks & Kanban API
Request/Response models dla walidacji i serializacji
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# =============================================================================
# TASK SCHEMAS
# =============================================================================

class TaskBase(BaseModel):
    """Bazowy schemat zadania"""
    id: str = Field(..., min_length=1, max_length=100, description="UUID zadania")
    title: str = Field(..., min_length=1, max_length=500, description="Tytuł zadania")
    description: Optional[str] = Field(None, description="Opis zadania")
    status: bool = Field(default=False, description="Status: False=todo, True=done")
    parent_id: Optional[str] = Field(None, description="ID zadania rodzica (dla subtasków)")
    
    # Dates
    due_date: Optional[datetime] = Field(None, description="Termin wykonania")
    completion_date: Optional[datetime] = Field(None, description="Data ukończenia")
    alarm_date: Optional[datetime] = Field(None, description="Data alarmu")
    
    # Relations
    note_id: Optional[int] = Field(None, description="ID powiązanej notatki")
    
    # Custom data
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="Dodatkowe dane JSON")
    
    # Metadata
    archived: bool = Field(default=False, description="Czy zarchiwizowane")
    order: int = Field(default=0, description="Kolejność sortowania")
    
    # Sync
    version: int = Field(default=1, ge=1, description="Wersja dla conflict resolution")
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Tytuł nie może być pusty')
        return v.strip()
    
    @validator('custom_data', pre=True)
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('custom_data musi być słownikiem')
        return v
    
    @validator('parent_id')
    def parent_not_self(cls, v, values):
        if v and 'id' in values and v == values['id']:
            raise ValueError('Zadanie nie może być rodzicem samego siebie')
        return v


class TaskCreate(TaskBase):
    """Schema dla tworzenia zadania (upsert)"""
    user_id: str = Field(..., description="ID użytkownika z autentykacji")


class TaskUpdate(BaseModel):
    """Schema dla aktualizacji zadania (partial update)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[bool] = None
    parent_id: Optional[str] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    alarm_date: Optional[datetime] = None
    note_id: Optional[int] = None
    custom_data: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None
    order: Optional[int] = None
    version: int = Field(..., ge=1, description="Aktualna wersja dla wykrywania konfliktów")


class TaskResponse(TaskBase):
    """Schema odpowiedzi zadania"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Pydantic v2


class ListTasksResponse(BaseModel):
    """Schema odpowiedzi listy zadań"""
    items: List[TaskResponse]
    count: int
    last_sync: Optional[datetime] = None


# =============================================================================
# TAG SCHEMAS
# =============================================================================

class TaskTagBase(BaseModel):
    """Bazowy schemat tagu"""
    id: str = Field(..., description="UUID tagu")
    name: str = Field(..., min_length=1, max_length=100, description="Nazwa tagu")
    color: str = Field(default='#CCCCCC', pattern=r'^#[0-9A-Fa-f]{6}$', description="Kolor HEX")
    version: int = Field(default=1, ge=1)
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Nazwa tagu nie może być pusta')
        return v.strip()


class TaskTagCreate(TaskTagBase):
    """Schema dla tworzenia tagu"""
    user_id: str = Field(..., description="ID użytkownika")


class TaskTagResponse(TaskTagBase):
    """Schema odpowiedzi tagu"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ListTagsResponse(BaseModel):
    """Schema odpowiedzi listy tagów"""
    items: List[TaskTagResponse]
    count: int


# =============================================================================
# TAG ASSIGNMENT SCHEMAS
# =============================================================================

class TaskTagAssignmentBase(BaseModel):
    """Bazowy schemat przypisania tagu"""
    id: str = Field(..., description="UUID przypisania")
    task_id: str = Field(..., description="ID zadania")
    tag_id: str = Field(..., description="ID tagu")


class TaskTagAssignmentCreate(TaskTagAssignmentBase):
    """Schema dla tworzenia przypisania"""
    pass


class TaskTagAssignmentResponse(TaskTagAssignmentBase):
    """Schema odpowiedzi przypisania"""
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# CUSTOM LIST SCHEMAS
# =============================================================================

class TaskCustomListBase(BaseModel):
    """Bazowy schemat custom listy"""
    id: str = Field(..., description="UUID listy")
    name: str = Field(..., min_length=1, max_length=100, description="Nazwa listy")
    values: List[str] = Field(default_factory=list, description="Wartości listy")
    version: int = Field(default=1, ge=1)
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Nazwa listy nie może być pusta')
        return v.strip()


class TaskCustomListCreate(TaskCustomListBase):
    """Schema dla tworzenia custom listy"""
    user_id: str = Field(..., description="ID użytkownika")


class TaskCustomListResponse(TaskCustomListBase):
    """Schema odpowiedzi custom listy"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ListCustomListsResponse(BaseModel):
    """Schema odpowiedzi listy custom lists"""
    items: List[TaskCustomListResponse]
    count: int


# =============================================================================
# KANBAN SCHEMAS
# =============================================================================

class KanbanItemBase(BaseModel):
    """Bazowy schemat pozycji Kanban"""
    id: str = Field(..., description="UUID pozycji Kanban")
    task_id: str = Field(..., description="ID zadania")
    column_type: Literal['todo', 'in_progress', 'done', 'on_hold', 'review'] = Field(..., description="Typ kolumny")
    position: int = Field(default=0, ge=0, description="Pozycja w kolumnie")
    version: int = Field(default=1, ge=1)


class KanbanItemCreate(KanbanItemBase):
    """Schema dla tworzenia pozycji Kanban"""
    user_id: str = Field(..., description="ID użytkownika")


class KanbanItemResponse(KanbanItemBase):
    """Schema odpowiedzi pozycji Kanban"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ListKanbanItemsResponse(BaseModel):
    """Schema odpowiedzi listy pozycji Kanban"""
    items: List[KanbanItemResponse]
    count: int


class KanbanMoveRequest(BaseModel):
    """Schema żądania przeniesienia zadania na Kanban"""
    task_id: str = Field(..., description="ID zadania")
    from_column: str = Field(..., description="Z której kolumny")
    to_column: str = Field(..., description="Do której kolumny")
    to_position: int = Field(..., ge=0, description="Na którą pozycję")
    version: int = Field(..., ge=1, description="Wersja dla conflict detection")


# =============================================================================
# KANBAN SETTINGS SCHEMAS
# =============================================================================

class KanbanSettingsBase(BaseModel):
    """Bazowy schemat ustawień Kanban"""
    id: str = Field(..., description="UUID ustawień")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Ustawienia JSON")
    version: int = Field(default=1, ge=1)
    
    @validator('settings', pre=True)
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('settings musi być słownikiem')
        return v


class KanbanSettingsCreate(KanbanSettingsBase):
    """Schema dla tworzenia ustawień Kanban"""
    user_id: str = Field(..., description="ID użytkownika")


class KanbanSettingsResponse(KanbanSettingsBase):
    """Schema odpowiedzi ustawień Kanban"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# COLUMNS CONFIG SCHEMAS
# =============================================================================

class ColumnsConfigBase(BaseModel):
    """Bazowy schemat konfiguracji kolumn"""
    id: str = Field(..., description="UUID konfiguracji")
    columns: List[Dict[str, Any]] = Field(default_factory=list, description="Konfiguracja kolumn")
    version: int = Field(default=1, ge=1)
    
    @validator('columns', pre=True)
    def ensure_list(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError('columns musi być listą')
        return v


class ColumnsConfigCreate(ColumnsConfigBase):
    """Schema dla tworzenia konfiguracji kolumn"""
    user_id: str = Field(..., description="ID użytkownika")


class ColumnsConfigResponse(ColumnsConfigBase):
    """Schema odpowiedzi konfiguracji kolumn"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# TASK HISTORY SCHEMAS
# =============================================================================

class TaskHistoryBase(BaseModel):
    """Bazowy schemat historii zadania"""
    task_id: str = Field(..., description="ID zadania")
    action_type: str = Field(..., description="Typ akcji")
    old_value: Optional[str] = Field(None, description="Stara wartość")
    new_value: Optional[str] = Field(None, description="Nowa wartość")
    details: Dict[str, Any] = Field(default_factory=dict, description="Szczegóły JSON")


class TaskHistoryCreate(TaskHistoryBase):
    """Schema dla tworzenia wpisu historii"""
    user_id: str = Field(..., description="ID użytkownika")


class TaskHistoryResponse(TaskHistoryBase):
    """Schema odpowiedzi historii"""
    id: int
    user_id: str
    created_at: datetime
    synced_at: Optional[datetime] = None
    version: int
    
    class Config:
        from_attributes = True


class ListTaskHistoryResponse(BaseModel):
    """Schema odpowiedzi listy historii"""
    items: List[TaskHistoryResponse]
    count: int


# =============================================================================
# BULK SYNC SCHEMAS
# =============================================================================

class BulkSyncRequest(BaseModel):
    """Schema żądania bulk sync"""
    user_id: str = Field(..., description="ID użytkownika")
    tasks: List[TaskBase] = Field(default_factory=list, description="Zadania do sync")
    tags: List[TaskTagBase] = Field(default_factory=list, description="Tagi do sync")
    tag_assignments: List[TaskTagAssignmentBase] = Field(default_factory=list, description="Przypisania tagów")
    kanban_items: List[KanbanItemBase] = Field(default_factory=list, description="Pozycje Kanban")
    custom_lists: List[TaskCustomListBase] = Field(default_factory=list, description="Custom listy")
    last_sync: Optional[datetime] = Field(None, description="Ostatnia synchronizacja klienta")
    
    @validator('tasks')
    def limit_tasks_count(cls, v):
        if len(v) > 100:
            raise ValueError('Maksymalnie 100 zadań na sync request')
        return v
    
    @validator('tags')
    def limit_tags_count(cls, v):
        if len(v) > 100:
            raise ValueError('Maksymalnie 100 tagów na sync request')
        return v


class BulkSyncItemResult(BaseModel):
    """Wynik dla pojedynczego item w bulk sync"""
    id: str = Field(..., description="ID elementu")
    entity_type: Literal['task', 'tag', 'tag_assignment', 'kanban_item', 'custom_list'] = Field(..., description="Typ encji")
    status: Literal['success', 'conflict', 'error'] = Field(..., description="Status operacji")
    version: Optional[int] = Field(None, description="Nowa wersja (jeśli success)")
    error: Optional[str] = Field(None, description="Komunikat błędu")
    server_version: Optional[int] = Field(None, description="Wersja serwera (jeśli conflict)")


class BulkSyncResponse(BaseModel):
    """Schema odpowiedzi bulk sync"""
    results: List[BulkSyncItemResult] = Field(..., description="Wyniki dla każdego elementu")
    success_count: int = Field(..., description="Liczba sukcesów")
    conflict_count: int = Field(..., description="Liczba konfliktów")
    error_count: int = Field(..., description="Liczba błędów")
    server_timestamp: datetime = Field(..., description="Timestamp serwera")


# =============================================================================
# OTHER SCHEMAS
# =============================================================================

class DeleteResponse(BaseModel):
    """Schema odpowiedzi usunięcia"""
    message: str = Field(..., description="Komunikat")
    id: str = Field(..., description="ID usuniętego elementu")
    deleted_at: datetime = Field(..., description="Timestamp usunięcia")


class ConflictErrorResponse(BaseModel):
    """Schema odpowiedzi konfliktu wersji"""
    detail: str = Field(default="Wykryto konflikt wersji", description="Opis błędu")
    local_version: int = Field(..., description="Wersja lokalna")
    server_version: int = Field(..., description="Wersja serwera")
    server_data: TaskResponse = Field(..., description="Dane z serwera")


class SyncStatsResponse(BaseModel):
    """Schema statystyk synchronizacji"""
    user_id: str
    last_sync: Optional[datetime]
    pending_tasks: int
    pending_tags: int
    pending_kanban_items: int
    total_tasks: int
    total_tags: int
