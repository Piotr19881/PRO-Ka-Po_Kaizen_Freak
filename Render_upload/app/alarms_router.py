"""
Alarms Router for PRO-Ka-Po API
Endpointy do synchronizacji alarmów i timerów w architekturze local-first
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from loguru import logger
import asyncio

from .database import get_db
from .auth import get_current_user, decode_token
from .alarms_models import AlarmTimer, AlarmsTimersSchema
from .websocket_manager import (
    manager,
    notify_item_change,
    notify_sync_required,
    WSEventType,
    handle_client_message,
    heartbeat_task
)

router = APIRouter(prefix="/api/alarms-timers", tags=["Alarms & Timers"])


# =============================================================================
# PYDANTIC MODELS (Request/Response schemas)
# =============================================================================

class AlarmTimerBase(BaseModel):
    """Bazowy schemat dla alarm/timer"""
    id: str
    type: Literal["alarm", "timer"]
    label: str = Field(..., min_length=1, max_length=200)
    enabled: bool = True
    
    # Alarm specific fields
    alarm_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    recurrence: Optional[Literal["once", "daily", "weekly", "weekdays", "weekends"]] = None
    days: Optional[List[int]] = Field(None, description="Days of week: 0-6 (Sunday-Saturday)")
    
    # Timer specific fields
    duration: Optional[int] = Field(None, ge=1, description="Duration in seconds")
    remaining: Optional[int] = Field(None, ge=0, description="Remaining seconds")
    repeat: Optional[bool] = None
    started_at: Optional[datetime] = None
    
    # Common settings
    play_sound: bool = True
    show_popup: bool = True
    custom_sound: Optional[str] = None
    
    # Sync metadata
    version: int = Field(default=1, ge=1)
    
    @validator('days')
    def validate_days(cls, v, values):
        """Walidacja dni tygodnia"""
        if v is not None:
            if not all(0 <= day <= 6 for day in v):
                raise ValueError("Days must be integers between 0 and 6")
            if len(v) != len(set(v)):
                raise ValueError("Days must be unique")
        return v
    
    @validator('alarm_time')
    def validate_alarm_fields(cls, v, values):
        """Walidacja że alarm ma wymagane pola"""
        if values.get('type') == 'alarm' and v is None:
            raise ValueError("alarm_time is required for type='alarm'")
        return v
    
    @validator('duration')
    def validate_timer_fields(cls, v, values):
        """Walidacja że timer ma wymagane pola"""
        if values.get('type') == 'timer' and v is None:
            raise ValueError("duration is required for type='timer'")
        return v


class UpsertAlarmTimerRequest(AlarmTimerBase):
    """Schemat żądania create/update"""
    user_id: str = Field(..., description="User ID from authentication")


class AlarmTimerResponse(AlarmTimerBase):
    """Schemat odpowiedzi pojedynczego item"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ListAlarmTimersResponse(BaseModel):
    """Schemat odpowiedzi listy items"""
    items: List[AlarmTimerResponse]
    count: int


class DeleteResponse(BaseModel):
    """Schemat odpowiedzi usunięcia"""
    message: str
    id: str
    deleted_at: Optional[datetime] = None


class ConflictErrorResponse(BaseModel):
    """Schemat odpowiedzi konfliktu wersji"""
    detail: str = "Version conflict detected"
    local_version: int
    server_version: int
    server_data: AlarmTimerResponse


class BulkSyncRequest(BaseModel):
    """Schemat żądania bulk sync"""
    user_id: str
    items: List[AlarmTimerBase]


class BulkSyncItemResult(BaseModel):
    """Wynik dla pojedynczego item w bulk sync"""
    id: str
    status: Literal["success", "conflict", "error"]
    version: Optional[int] = None
    error: Optional[str] = None
    server_version: Optional[int] = None


class BulkSyncResponse(BaseModel):
    """Schemat odpowiedzi bulk sync"""
    results: List[BulkSyncItemResult]
    success_count: int
    error_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def db_model_to_response(db_item: AlarmTimer) -> AlarmTimerResponse:
    """Konwertuj model DB na response schema"""
    # Konwertuj alarm_time jeśli to time object
    alarm_time_str = None
    if db_item.alarm_time:
        if isinstance(db_item.alarm_time, str):
            alarm_time_str = db_item.alarm_time
        else:
            # Jeśli to time object, konwertuj na string
            alarm_time_str = db_item.alarm_time.strftime("%H:%M")
    
    return AlarmTimerResponse(
        id=db_item.id,
        user_id=db_item.user_id,
        type=db_item.type,
        label=db_item.label,
        enabled=db_item.enabled,
        alarm_time=alarm_time_str,
        recurrence=db_item.recurrence,
        days=db_item.days,
        duration=db_item.duration,
        remaining=db_item.remaining,
        repeat=db_item.repeat,
        started_at=db_item.started_at,
        play_sound=db_item.play_sound,
        show_popup=db_item.show_popup,
        custom_sound=db_item.custom_sound,
        created_at=db_item.created_at,
        updated_at=db_item.updated_at,
        synced_at=db_item.synced_at,
        deleted_at=db_item.deleted_at,
        version=db_item.version
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "alarms-timers",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("", response_model=AlarmTimerResponse, status_code=status.HTTP_200_OK)
async def upsert_alarm_timer(
    request: UpsertAlarmTimerRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Utwórz lub zaktualizuj alarm/timer (upsert).
    
    Obsługuje:
    - Tworzenie nowego alarmu/timera
    - Aktualizację istniejącego
    - Wykrywanie konfliktów wersji (409)
    """
    try:
        # Weryfikacja że user_id zgadza się z authenticated user
        if request.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create/update items for other users"
            )
        
        # Sprawdź czy item już istnieje
        existing = db.query(AlarmTimer).filter(
            AlarmTimer.id == request.id,
            AlarmTimer.user_id == request.user_id
        ).first()
        
        if existing:
            # Update - sprawdź wersję
            # Konflikt jeśli: serwer ma nowszą ALBO równą wersję (nie powinno się wysyłać tej samej wersji dwa razy)
            if existing.version >= request.version:
                # Konflikt wersji - serwer ma nowszą lub taką samą wersję
                logger.warning(f"Version conflict for {request.id}: server={existing.version}, client={request.version}")
                
                # Konwertuj server data do JSON-serializable format
                server_response = db_model_to_response(existing)
                server_data = server_response.model_dump(mode='json')
                
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "detail": "Version conflict detected",
                        "local_version": request.version,
                        "server_version": existing.version,
                        "server_data": server_data
                    }
                )
            
            # Update istniejącego
            existing.type = request.type
            existing.label = request.label
            existing.enabled = request.enabled
            existing.alarm_time = request.alarm_time
            existing.recurrence = request.recurrence
            existing.days = request.days
            existing.duration = request.duration
            existing.remaining = request.remaining
            existing.repeat = request.repeat
            existing.started_at = request.started_at
            existing.play_sound = request.play_sound
            existing.show_popup = request.show_popup
            existing.custom_sound = request.custom_sound
            existing.updated_at = datetime.utcnow()
            existing.synced_at = datetime.utcnow()
            existing.version = request.version + 1
            existing.deleted_at = None  # Undelete jeśli był soft deleted
            
            db.commit()
            db.refresh(existing)
            
            logger.info(f"Updated {request.type} {request.id} for user {request.user_id}")
            
            # WebSocket notification - updated
            response_data = db_model_to_response(existing)
            event_type = WSEventType.ALARM_UPDATED if request.type == "alarm" else WSEventType.TIMER_UPDATED
            asyncio.create_task(notify_item_change(event_type, response_data.model_dump(mode='json'), request.user_id))
            
            return response_data
        
        else:
            # Create nowego
            new_item = AlarmTimer(
                id=request.id,
                user_id=request.user_id,
                type=request.type,
                label=request.label,
                enabled=request.enabled,
                alarm_time=request.alarm_time,
                recurrence=request.recurrence,
                days=request.days,
                duration=request.duration,
                remaining=request.remaining,
                repeat=request.repeat,
                started_at=request.started_at,
                play_sound=request.play_sound,
                show_popup=request.show_popup,
                custom_sound=request.custom_sound,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                synced_at=datetime.utcnow(),
                version=request.version
            )
            
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            
            logger.info(f"Created {request.type} {request.id} for user {request.user_id}")
            
            # WebSocket notification - created
            response_data = db_model_to_response(new_item)
            event_type = WSEventType.ALARM_CREATED if request.type == "alarm" else WSEventType.TIMER_CREATED
            asyncio.create_task(notify_item_change(event_type, response_data.model_dump(mode='json'), request.user_id))
            
            return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upsert_alarm_timer: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("", response_model=ListAlarmTimersResponse, status_code=status.HTTP_200_OK)
async def list_alarm_timers(
    user_id: str = Query(..., description="User ID"),
    type: Optional[Literal["alarm", "timer"]] = Query(None, description="Filter by type"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Pobierz wszystkie alarmy/timery użytkownika.
    
    Parametry:
    - user_id: ID użytkownika (wymagane)
    - type: Filtr typu (opcjonalne)
    - enabled: Filtr aktywnych (opcjonalne)
    """
    try:
        # Weryfikacja uprawnień
        if user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access items of other users"
            )
        
        # Build query
        query = db.query(AlarmTimer).filter(
            AlarmTimer.user_id == user_id,
            AlarmTimer.deleted_at.is_(None)  # Tylko nie-usunięte
        )
        
        # Apply filters
        if type:
            query = query.filter(AlarmTimer.type == type)
        if enabled is not None:
            query = query.filter(AlarmTimer.enabled == enabled)
        
        # Order by created_at
        query = query.order_by(AlarmTimer.created_at.desc())
        
        items = query.all()
        
        logger.info(f"Retrieved {len(items)} items for user {user_id}")
        
        return ListAlarmTimersResponse(
            items=[db_model_to_response(item) for item in items],
            count=len(items)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_alarm_timers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{item_id}", response_model=AlarmTimerResponse, status_code=status.HTTP_200_OK)
async def get_alarm_timer(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pobierz konkretny alarm/timer po ID"""
    try:
        item = db.query(AlarmTimer).filter(
            AlarmTimer.id == item_id,
            AlarmTimer.deleted_at.is_(None)
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Weryfikacja uprawnień
        if item.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        logger.info(f"Retrieved {item.type} {item_id}")
        return db_model_to_response(item)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_alarm_timer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/{item_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_alarm_timer(
    item_id: str,
    soft: bool = Query(True, description="Soft delete (true) or hard delete (false)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Usuń alarm/timer.
    
    Parametry:
    - item_id: ID alarmu/timera
    - soft: Soft delete (domyślnie true) lub hard delete (false)
    """
    try:
        item = db.query(AlarmTimer).filter(AlarmTimer.id == item_id).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found"
            )
        
        # Weryfikacja uprawnień
        if item.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        item_type = item.type
        user_id = item.user_id
        
        if soft:
            # Soft delete - ustaw deleted_at
            item.deleted_at = datetime.utcnow()
            item.updated_at = datetime.utcnow()
            item.version += 1
            db.commit()
            
            logger.info(f"Soft deleted {item.type} {item_id}")
            
            # WebSocket notification - deleted
            event_type = WSEventType.ALARM_DELETED if item_type == "alarm" else WSEventType.TIMER_DELETED
            asyncio.create_task(notify_item_change(event_type, {"id": item_id, "deleted_at": item.deleted_at.isoformat()}, user_id))
            
            return DeleteResponse(
                message="Item soft deleted successfully",
                id=item_id,
                deleted_at=item.deleted_at
            )
        else:
            # Hard delete - usuń z bazy
            db.delete(item)
            db.commit()
            
            logger.info(f"Hard deleted {item.type} {item_id}")
            
            # WebSocket notification - deleted
            event_type = WSEventType.ALARM_DELETED if item_type == "alarm" else WSEventType.TIMER_DELETED
            asyncio.create_task(notify_item_change(event_type, {"id": item_id, "deleted_at": None}, user_id))
            
            return DeleteResponse(
                message="Item hard deleted successfully",
                id=item_id,
                deleted_at=None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_alarm_timer: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/bulk", response_model=BulkSyncResponse, status_code=status.HTTP_200_OK)
async def bulk_sync(
    request: BulkSyncRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronizuj wiele elementów w jednym request.
    
    Returns 200 nawet przy częściowych błędach - sprawdź results[].status
    """
    try:
        # Weryfikacja uprawnień
        if request.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot sync items for other users"
            )
        
        results = []
        success_count = 0
        error_count = 0
        
        for item_data in request.items:
            try:
                # Konwertuj na UpsertRequest z obsługą błędów walidacji
                try:
                    upsert_request = UpsertAlarmTimerRequest(
                        user_id=request.user_id,
                        **item_data.dict()
                    )
                except ValueError as ve:
                    # Błąd walidacji Pydantic
                    logger.error(f"Validation error for item {item_data.id}: {ve}")
                    results.append(BulkSyncItemResult(
                        id=item_data.id,
                        status="error",
                        error=f"Validation error: {str(ve)}"
                    ))
                    error_count += 1
                    continue
                
                # Próbuj upsert
                existing = db.query(AlarmTimer).filter(
                    AlarmTimer.id == upsert_request.id,
                    AlarmTimer.user_id == request.user_id
                ).first()
                
                if existing and existing.version >= upsert_request.version:
                    # Konflikt wersji
                    results.append(BulkSyncItemResult(
                        id=upsert_request.id,
                        status="conflict",
                        error="Version mismatch",
                        server_version=existing.version
                    ))
                    error_count += 1
                    continue
                
                if existing:
                    # Update
                    existing.label = upsert_request.label
                    existing.enabled = upsert_request.enabled
                    existing.alarm_time = upsert_request.alarm_time
                    existing.recurrence = upsert_request.recurrence
                    existing.days = upsert_request.days
                    existing.duration = upsert_request.duration
                    existing.remaining = upsert_request.remaining
                    existing.repeat = upsert_request.repeat
                    existing.started_at = upsert_request.started_at
                    existing.play_sound = upsert_request.play_sound
                    existing.show_popup = upsert_request.show_popup
                    existing.custom_sound = upsert_request.custom_sound
                    existing.updated_at = datetime.utcnow()
                    existing.synced_at = datetime.utcnow()
                    existing.version = upsert_request.version + 1
                    existing.deleted_at = None
                    
                    results.append(BulkSyncItemResult(
                        id=upsert_request.id,
                        status="success",
                        version=existing.version
                    ))
                else:
                    # Create
                    new_item = AlarmTimer(
                        id=upsert_request.id,
                        user_id=request.user_id,
                        type=upsert_request.type,
                        label=upsert_request.label,
                        enabled=upsert_request.enabled,
                        alarm_time=upsert_request.alarm_time,
                        recurrence=upsert_request.recurrence,
                        days=upsert_request.days,
                        duration=upsert_request.duration,
                        remaining=upsert_request.remaining,
                        repeat=upsert_request.repeat,
                        started_at=upsert_request.started_at,
                        play_sound=upsert_request.play_sound,
                        show_popup=upsert_request.show_popup,
                        custom_sound=upsert_request.custom_sound,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        synced_at=datetime.utcnow(),
                        version=upsert_request.version
                    )
                    db.add(new_item)
                    
                    results.append(BulkSyncItemResult(
                        id=upsert_request.id,
                        status="success",
                        version=new_item.version
                    ))
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing item {item_data.id}: {e}")
                results.append(BulkSyncItemResult(
                    id=item_data.id,
                    status="error",
                    error=str(e)
                ))
                error_count += 1
        
        # Commit wszystkich zmian
        db.commit()
        
        logger.info(f"Bulk sync completed: {success_count} success, {error_count} errors")
        
        return BulkSyncResponse(
            results=results,
            success_count=success_count,
            error_count=error_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk_sync: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint dla real-time synchronizacji.
    
    Query Parameters:
        token: JWT access token dla autentykacji
    
    Message Format (Client -> Server):
        {
            "type": "ping" | "subscribe" | "unsubscribe",
            "timestamp": "ISO datetime"
        }
    
    Message Format (Server -> Client):
        {
            "type": "alarm_created" | "alarm_updated" | "alarm_deleted" |
                    "timer_created" | "timer_updated" | "timer_deleted" |
                    "sync_required" | "heartbeat" | "error",
            "timestamp": "ISO datetime",
            "user_id": "string",
            "data": {...}  # dla item events
        }
    
    Usage:
        ws = new WebSocket("ws://localhost:8000/api/alarms-timers/ws?token=YOUR_JWT_TOKEN")
        
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'alarm_updated') {
                // Odśwież UI
            }
        }
    """
    user_id = None
    heartbeat_task_handle = None
    
    try:
        # Autentykacja przez JWT token
        try:
            payload = decode_token(token)
            user_id = payload.get("user_id") or payload.get("sub")  # sub is the user_id in JWT
            
            if not user_id:
                await websocket.close(code=1008, reason="Invalid token: missing user_id")
                return
        
        except Exception as e:
            logger.error(f"WebSocket auth error: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Połącz WebSocket
        await manager.connect(websocket, user_id)
        
        # Wyślij potwierdzenie połączenia
        await manager.send_personal_message({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "message": "WebSocket connection established"
        }, websocket)
        
        # Uruchom heartbeat task
        heartbeat_task_handle = asyncio.create_task(heartbeat_task(websocket, interval=30))
        
        # Główna pętla - odbieraj wiadomości od klienta
        while True:
            try:
                # Odbierz wiadomość jako JSON
                data = await websocket.receive_json()
                
                # Obsłuż wiadomość
                await handle_client_message(data, websocket, user_id)
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected normally: user={user_id}")
                break
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                # Wyślij error ale nie rozłączaj
                await manager.send_personal_message({
                    "type": WSEventType.ERROR,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": "Error processing message",
                    "details": str(e)
                }, websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # Zatrzymaj heartbeat
        if heartbeat_task_handle:
            heartbeat_task_handle.cancel()
        
        # Rozłącz
        if user_id:
            await manager.disconnect(websocket, user_id)
        
        logger.info(f"WebSocket closed: user={user_id}")


@router.get("/ws/stats", response_model=dict)
async def websocket_stats(current_user: dict = Depends(get_current_user)):
    """
    Zwróć statystyki połączeń WebSocket (admin only).
    
    Returns:
        {
            "total_users": int,
            "total_connections": int,
            "users": {
                "user_id": connection_count
            }
        }
    """
    return manager.get_stats()

