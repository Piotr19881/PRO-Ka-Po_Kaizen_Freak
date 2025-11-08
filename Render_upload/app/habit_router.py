"""
FastAPI Router dla Habit Tracker synchronizacji
Endpoints: /api/habits
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime, date
import logging

from .database import get_db

# Logger dla habit tracker operations
logger = logging.getLogger("habit_tracker")
from .habit_models import HabitColumn, HabitRecord
from .habit_schemas import (
    HabitColumnCreate, HabitColumnUpdate, HabitColumnResponse,
    HabitRecordCreate, HabitRecordUpdate, HabitRecordResponse,
    BulkHabitSyncRequest, BulkHabitSyncResponse, BulkHabitSyncItemResult,
    MonthlyDataRequest, MonthlyDataResponse,
    DeleteResponse, ConflictErrorResponse,
    ListHabitColumnsResponse, ListHabitRecordsResponse
)

router = APIRouter(prefix="/api/habits", tags=["habits"])


# =============================================================================
# HABIT COLUMNS ENDPOINTS
# =============================================================================

@router.get("/columns", response_model=ListHabitColumnsResponse)
async def get_habit_columns(
    user_id: str,
    last_sync: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Pobiera wszystkie kolumny nawyków użytkownika
    Opcjonalnie filtruje po last_sync (incremental sync)
    """
    logger.info(f"🏃 HABIT TRACKER: GET /columns dla user_id={user_id}, last_sync={last_sync}")
    
    query = db.query(HabitColumn).filter(
        and_(
            HabitColumn.user_id == user_id,
            HabitColumn.deleted_at.is_(None)
        )
    )
    
    if last_sync:
        query = query.filter(HabitColumn.updated_at > last_sync)
        logger.info(f"🔄 HABIT TRACKER: Incremental sync - filtrowanie po {last_sync}")
    
    columns = query.order_by(HabitColumn.position).all()
    
    logger.info(f"📊 HABIT TRACKER: Znaleziono {len(columns)} kolumn dla user {user_id}")
    if columns:
        logger.info(f"🎯 HABIT TRACKER: Kolumny: {[f'{col.name}(id={col.id})' for col in columns[:5]]}")
    
    return ListHabitColumnsResponse(
        items=columns,
        count=len(columns),
        last_sync=datetime.utcnow()
    )


@router.post("/columns", response_model=HabitColumnResponse)
async def create_habit_column(
    column_data: HabitColumnCreate,
    db: Session = Depends(get_db)
):
    """Tworzy nową kolumnę nawyku"""
    
    # Sprawdź czy nazwa nie istnieje już
    existing = db.query(HabitColumn).filter(
        and_(
            HabitColumn.user_id == column_data.user_id,
            HabitColumn.name == column_data.name,
            HabitColumn.deleted_at.is_(None)
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Habit column '{column_data.name}' already exists"
        )
    
    # Utwórz nową kolumnę
    db_column = HabitColumn(**column_data.dict())
    db.add(db_column)
    db.commit()
    db.refresh(db_column)
    
    return db_column


@router.put("/columns/{column_id}", response_model=HabitColumnResponse)
async def update_habit_column(
    column_id: str,
    column_data: HabitColumnUpdate,
    db: Session = Depends(get_db)
):
    """Aktualizuje kolumnę nawyku"""
    
    db_column = db.query(HabitColumn).filter(HabitColumn.id == column_id).first()
    if not db_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit column not found"
        )
    
    # Sprawdź version dla conflict detection
    if db_column.version != column_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictErrorResponse(
                local_version=column_data.version,
                server_version=db_column.version,
                server_data=HabitColumnResponse.from_orm(db_column).dict()
            ).dict()
        )
    
    # Aktualizuj pola
    update_data = column_data.dict(exclude_unset=True, exclude={'version'})
    for field, value in update_data.items():
        setattr(db_column, field, value)
    
    # Increment version
    db_column.version += 1
    db_column.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_column)
    
    return db_column


@router.delete("/columns/{column_id}", response_model=DeleteResponse)
async def delete_habit_column(
    column_id: str,
    db: Session = Depends(get_db)
):
    """Usuwa kolumnę nawyku (soft delete)"""
    
    db_column = db.query(HabitColumn).filter(HabitColumn.id == column_id).first()
    if not db_column:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit column not found"
        )
    
    # Soft delete
    db_column.deleted_at = datetime.utcnow()
    db_column.updated_at = datetime.utcnow()
    db_column.version += 1
    
    db.commit()
    
    return DeleteResponse(
        message="Habit column deleted successfully",
        id=column_id,
        deleted_at=db_column.deleted_at
    )


# =============================================================================
# HABIT RECORDS ENDPOINTS
# =============================================================================

@router.get("/records", response_model=ListHabitRecordsResponse)
async def get_habit_records(
    user_id: str,
    habit_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    last_sync: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Pobiera rekordy nawyków użytkownika
    Opcjonalnie filtruje po habit_id, dacie lub last_sync
    """
    logger.info(f"📝 HABIT TRACKER: GET /records dla user_id={user_id}")
    logger.info(f"🔍 HABIT TRACKER: Filtry - habit_id={habit_id}, start_date={start_date}, end_date={end_date}, last_sync={last_sync}")
    
    query = db.query(HabitRecord).filter(HabitRecord.user_id == user_id)
    
    if habit_id:
        query = query.filter(HabitRecord.habit_id == habit_id)
    
    if start_date:
        query = query.filter(HabitRecord.date >= start_date)
    
    if end_date:
        query = query.filter(HabitRecord.date <= end_date)
    
    if last_sync:
        query = query.filter(HabitRecord.updated_at > last_sync)
        logger.info(f"🔄 HABIT TRACKER: Incremental sync - filtrowanie rekordów po {last_sync}")
    
    records = query.order_by(HabitRecord.date.desc()).all()
    
    logger.info(f"📊 HABIT TRACKER: Znaleziono {len(records)} rekordów dla user {user_id}")
    if records:
        logger.info(f"🎯 HABIT TRACKER: Przykłady rekordów: {[f'{rec.date}:{rec.habit_id}={rec.value}' for rec in records[:3]]}")
    
    return ListHabitRecordsResponse(
        items=records,
        count=len(records),
        last_sync=datetime.utcnow()
    )


@router.post("/records", response_model=HabitRecordResponse)
async def create_habit_record(
    record_data: HabitRecordCreate,
    db: Session = Depends(get_db)
):
    """Tworzy nowy rekord nawyku"""
    
    # Sprawdź czy rekord już istnieje (user_id, habit_id, date)
    existing = db.query(HabitRecord).filter(
        and_(
            HabitRecord.user_id == record_data.user_id,
            HabitRecord.habit_id == record_data.habit_id,
            HabitRecord.date == record_data.date
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Habit record for this date already exists"
        )
    
    # Utwórz nowy rekord
    db_record = HabitRecord(**record_data.dict())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    return db_record


@router.put("/records/{record_id}", response_model=HabitRecordResponse)
async def update_habit_record(
    record_id: str,
    record_data: HabitRecordUpdate,
    db: Session = Depends(get_db)
):
    """Aktualizuje rekord nawyku"""
    
    db_record = db.query(HabitRecord).filter(HabitRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit record not found"
        )
    
    # Sprawdź version dla conflict detection
    if db_record.version != record_data.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ConflictErrorResponse(
                local_version=record_data.version,
                server_version=db_record.version,
                server_data=HabitRecordResponse.from_orm(db_record).dict()
            ).dict()
        )
    
    # Aktualizuj wartość
    if record_data.value is not None:
        db_record.value = record_data.value
    
    # Increment version
    db_record.version += 1
    db_record.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_record)
    
    return db_record


@router.delete("/records/{record_id}", response_model=DeleteResponse)
async def delete_habit_record(
    record_id: str,
    db: Session = Depends(get_db)
):
    """Usuwa rekord nawyku"""
    
    db_record = db.query(HabitRecord).filter(HabitRecord.id == record_id).first()
    if not db_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit record not found"
        )
    
    db.delete(db_record)
    db.commit()
    
    return DeleteResponse(
        message="Habit record deleted successfully",
        id=record_id,
        deleted_at=datetime.utcnow()
    )


# =============================================================================
# BULK SYNC ENDPOINT
# =============================================================================

@router.post("/sync", response_model=BulkHabitSyncResponse)
async def bulk_habit_sync(
    sync_data: BulkHabitSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk synchronization dla habit tracker
    Obsługuje kolumny i rekordy w jednym request
    """
    logger.info(f"🔄 HABIT TRACKER: BULK SYNC rozpoczęty dla user_id={sync_data.user_id}")
    logger.info(f"📊 HABIT TRACKER: Sync zawiera {len(sync_data.columns)} kolumn i {len(sync_data.records)} rekordów")
    
    results = []
    success_count = 0
    conflict_count = 0
    error_count = 0
    
    # Sync columns
    for column_data in sync_data.columns:
        try:
            # Sprawdź czy kolumna już istnieje
            existing_column = db.query(HabitColumn).filter(HabitColumn.id == column_data.id).first()
            
            if existing_column:
                # Update existing
                if existing_column.version < column_data.version:
                    # Server version is newer
                    for field, value in column_data.dict(exclude={'version'}).items():
                        if hasattr(existing_column, field):
                            setattr(existing_column, field, value)
                    existing_column.version = column_data.version
                    existing_column.updated_at = datetime.utcnow()
                    success_count += 1
                    results.append(BulkHabitSyncItemResult(
                        id=column_data.id,
                        entity_type="column",
                        status="success",
                        version=column_data.version
                    ))
                else:
                    # Conflict
                    conflict_count += 1
                    results.append(BulkHabitSyncItemResult(
                        id=column_data.id,
                        entity_type="column",
                        status="conflict",
                        version=existing_column.version,
                        server_version=existing_column.version
                    ))
            else:
                # Create new
                new_column = HabitColumn(**column_data.dict(), user_id=sync_data.user_id)
                db.add(new_column)
                success_count += 1
                results.append(BulkHabitSyncItemResult(
                    id=column_data.id,
                    entity_type="column",
                    status="success",
                    version=column_data.version
                ))
        
        except Exception as e:
            error_count += 1
            results.append(BulkHabitSyncItemResult(
                id=column_data.id,
                entity_type="column",
                status="error",
                error=str(e)
            ))
    
    # Sync records
    for record_data in sync_data.records:
        try:
            existing_record = db.query(HabitRecord).filter(HabitRecord.id == record_data.id).first()
            
            if existing_record:
                # Update existing
                if existing_record.version < record_data.version:
                    for field, value in record_data.dict(exclude={'version'}).items():
                        if hasattr(existing_record, field):
                            setattr(existing_record, field, value)
                    existing_record.version = record_data.version
                    existing_record.updated_at = datetime.utcnow()
                    success_count += 1
                    results.append(BulkHabitSyncItemResult(
                        id=record_data.id,
                        entity_type="record",
                        status="success",
                        version=record_data.version
                    ))
                else:
                    conflict_count += 1
                    results.append(BulkHabitSyncItemResult(
                        id=record_data.id,
                        entity_type="record",
                        status="conflict",
                        version=existing_record.version,
                        server_version=existing_record.version
                    ))
            else:
                # Create new
                new_record = HabitRecord(**record_data.dict(), user_id=sync_data.user_id)
                db.add(new_record)
                success_count += 1
                results.append(BulkHabitSyncItemResult(
                    id=record_data.id,
                    entity_type="record", 
                    status="success",
                    version=record_data.version
                ))
        
        except Exception as e:
            error_count += 1
            results.append(BulkHabitSyncItemResult(
                id=record_data.id,
                entity_type="record",
                status="error",
                error=str(e)
            ))
    
    db.commit()
    
    return BulkHabitSyncResponse(
        results=results,
        success_count=success_count,
        conflict_count=conflict_count,
        error_count=error_count,
        server_timestamp=datetime.utcnow()
    )


# =============================================================================
# MONTHLY DATA ENDPOINT
# =============================================================================

@router.post("/monthly", response_model=MonthlyDataResponse)
async def get_monthly_data(
    request: MonthlyDataRequest,
    db: Session = Depends(get_db)
):
    """
    Pobiera wszystkie dane dla konkretnego miesiąca
    Optymalizowane dla habit tracker calendar view
    """
    # Oblicz zakres dat
    if request.month == 12:
        start_date = date(request.year, request.month, 1)
        end_date = date(request.year + 1, 1, 1)
    else:
        start_date = date(request.year, request.month, 1)
        end_date = date(request.year, request.month + 1, 1)
    
    # Pobierz kolumny
    columns = db.query(HabitColumn).filter(
        and_(
            HabitColumn.user_id == request.user_id,
            HabitColumn.deleted_at.is_(None)
        )
    ).order_by(HabitColumn.position).all()
    
    # Pobierz rekordy dla miesiąca
    records = db.query(HabitRecord).filter(
        and_(
            HabitRecord.user_id == request.user_id,
            HabitRecord.date >= start_date,
            HabitRecord.date < end_date
        )
    ).order_by(HabitRecord.date).all()
    
    return MonthlyDataResponse(
        columns=columns,
        records=records,
        month=request.month,
        year=request.year,
        last_sync=datetime.utcnow()
    )