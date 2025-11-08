"""
Pydantic Schemas dla Habit Tracker API
Request/Response models dla walidacji i serializacji
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date


# =============================================================================
# HABIT COLUMN SCHEMAS
# =============================================================================

class HabitColumnBase(BaseModel):
    """Bazowy schemat kolumny nawyku"""
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal['checkbox', 'counter', 'duration', 'time', 'scale', 'text']
    position: int = Field(default=0, ge=0)
    scale_max: int = Field(default=10, ge=1, le=100)
    version: int = Field(default=1, ge=1)
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class HabitColumnCreate(HabitColumnBase):
    """Schema dla tworzenia kolumny nawyku"""
    user_id: str = Field(..., description="User ID from authentication")


class HabitColumnUpdate(BaseModel):
    """Schema dla aktualizacji kolumny nawyku"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[Literal['checkbox', 'counter', 'duration', 'time', 'scale', 'text']] = None
    position: Optional[int] = Field(None, ge=0)
    scale_max: Optional[int] = Field(None, ge=1, le=100)
    version: int = Field(..., ge=1, description="Current version for conflict detection")


class HabitColumnResponse(HabitColumnBase):
    """Schema odpowiedzi kolumny nawyku"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# HABIT RECORD SCHEMAS
# =============================================================================

class HabitRecordBase(BaseModel):
    """Bazowy schemat rekordu nawyku"""
    id: str = Field(..., min_length=1, max_length=100)
    habit_id: str = Field(..., min_length=1, max_length=100)
    date: date
    value: Optional[str] = Field(None, max_length=500)
    version: int = Field(default=1, ge=1)


class HabitRecordCreate(HabitRecordBase):
    """Schema dla tworzenia rekordu nawyku"""
    user_id: str


class HabitRecordUpdate(BaseModel):
    """Schema dla aktualizacji rekordu nawyku"""
    value: Optional[str] = Field(None, max_length=500)
    version: int = Field(..., ge=1, description="Current version for conflict detection")


class HabitRecordResponse(HabitRecordBase):
    """Schema odpowiedzi rekordu nawyku"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# BULK SYNC SCHEMAS
# =============================================================================

class BulkHabitSyncRequest(BaseModel):
    """Schema żądania bulk sync dla habit tracker"""
    user_id: str
    columns: List[HabitColumnBase] = Field(default_factory=list)
    records: List[HabitRecordBase] = Field(default_factory=list)
    last_sync: Optional[datetime] = None
    
    @validator('columns')
    def limit_columns_count(cls, v):
        if len(v) > 50:
            raise ValueError('Maximum 50 habit columns per sync request')
        return v
    
    @validator('records')
    def limit_records_count(cls, v):
        if len(v) > 200:
            raise ValueError('Maximum 200 habit records per sync request')
        return v


class BulkHabitSyncItemResult(BaseModel):
    """Wynik dla pojedynczego item w bulk sync"""
    id: str
    entity_type: Literal['column', 'record']
    status: Literal['success', 'conflict', 'error']
    version: Optional[int] = None
    error: Optional[str] = None
    server_version: Optional[int] = None


class BulkHabitSyncResponse(BaseModel):
    """Schema odpowiedzi bulk sync"""
    results: List[BulkHabitSyncItemResult]
    success_count: int
    conflict_count: int
    error_count: int
    server_timestamp: datetime


# =============================================================================
# MONTHLY DATA SCHEMAS
# =============================================================================

class MonthlyDataRequest(BaseModel):
    """Schema żądania danych miesięcznych"""
    user_id: str
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)


class MonthlyDataResponse(BaseModel):
    """Schema odpowiedzi danych miesięcznych"""
    columns: List[HabitColumnResponse]
    records: List[HabitRecordResponse]
    month: int
    year: int
    last_sync: Optional[datetime] = None


# =============================================================================
# OTHER SCHEMAS
# =============================================================================

class DeleteResponse(BaseModel):
    """Schema odpowiedzi usunięcia"""
    message: str
    id: str
    deleted_at: datetime


class ConflictErrorResponse(BaseModel):
    """Schema odpowiedzi konfliktu wersji"""
    detail: str = "Version conflict detected"
    local_version: int
    server_version: int
    server_data: Dict[str, Any]


class ListHabitColumnsResponse(BaseModel):
    """Schema odpowiedzi listy kolumn nawyków"""
    items: List[HabitColumnResponse]
    count: int
    last_sync: Optional[datetime] = None


class ListHabitRecordsResponse(BaseModel):
    """Schema odpowiedzi listy rekordów nawyków"""
    items: List[HabitRecordResponse]
    count: int
    last_sync: Optional[datetime] = None


# =============================================================================
# UWAGA: Brak HabitSettings schemas 
# Wszystkie ustawienia UI zarządzane tylko lokalnie
# =============================================================================