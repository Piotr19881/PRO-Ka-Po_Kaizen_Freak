"""
Pomodoro Router for PRO-Ka-Po API
Endpointy do synchronizacji sesji Pomodoro w architekturze local-first
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime, date
from loguru import logger
import asyncio
import uuid

from .database import get_db
from .auth import get_current_user
from .pomodoro_models import SessionTopic, SessionLog

router = APIRouter(prefix="/api/pomodoro", tags=["Pomodoro"])


# =============================================================================
# PYDANTIC MODELS (Request/Response schemas)
# =============================================================================

class TopicBase(BaseModel):
    """Bazowy schemat dla tematu sesji"""
    local_id: str = Field(..., description="Local ID from client device")
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default='#FF6B6B', pattern=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(default='📚', max_length=50)
    description: Optional[str] = None
    
    # Statystyki
    total_sessions: int = Field(default=0, ge=0)
    total_work_time: int = Field(default=0, ge=0)
    total_break_time: int = Field(default=0, ge=0)
    
    # Widoczność
    sort_order: int = Field(default=0)
    is_active: bool = True
    is_favorite: bool = False
    
    # Sync metadata
    version: int = Field(default=1, ge=1)
    last_modified: datetime


class UpsertTopicRequest(TopicBase):
    """Schemat żądania create/update tematu"""
    pass  # user_id będzie dodane automatycznie z tokenu


class TopicResponse(TopicBase):
    """Schemat odpowiedzi pojedynczego tematu"""
    server_id: str = Field(..., description="Server-generated UUID")
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SessionBase(BaseModel):
    """Bazowy schemat dla logu sesji"""
    local_id: str = Field(..., description="Local ID from client device")
    topic_id: Optional[str] = None
    
    # Dane czasowe
    session_date: date
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    # Czasy trwania
    work_duration: int = Field(..., ge=1, description="Planowany czas pracy (minuty)")
    short_break_duration: Optional[int] = Field(None, ge=1)
    long_break_duration: Optional[int] = Field(None, ge=1)
    actual_work_time: Optional[int] = Field(None, ge=0)
    actual_break_time: Optional[int] = Field(None, ge=0)
    
    # Status i typ
    session_type: Literal['work', 'short_break', 'long_break'] = 'work'
    status: Literal['completed', 'interrupted', 'skipped'] = 'completed'
    pomodoro_count: int = Field(default=1, ge=1, le=4)
    
    # Dodatkowe dane
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    productivity_rating: Optional[int] = Field(None, ge=1, le=5)
    
    # Sync metadata
    version: int = Field(default=1, ge=1)
    last_modified: datetime
    
    @validator('ended_at')
    def validate_times(cls, v, values):
        """Walidacja że ended_at >= started_at"""
        if v and 'started_at' in values and values['started_at']:
            if v < values['started_at']:
                raise ValueError("ended_at must be after started_at")
        return v


class UpsertSessionRequest(SessionBase):
    """Schemat żądania create/update sesji"""
    pass  # user_id będzie dodane automatycznie z tokenu


class SessionResponse(SessionBase):
    """Schemat odpowiedzi pojedynczej sesji"""
    server_id: str = Field(..., description="Server-generated UUID")
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ListTopicsResponse(BaseModel):
    """Schemat odpowiedzi listy tematów"""
    topics: List[TopicResponse]
    count: int


class ListSessionsResponse(BaseModel):
    """Schemat odpowiedzi listy sesji"""
    sessions: List[SessionResponse]
    count: int


class AllDataResponse(BaseModel):
    """Schemat odpowiedzi pobierania wszystkich danych"""
    topics: List[TopicResponse]
    sessions: List[SessionResponse]
    topics_count: int
    sessions_count: int


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
    server_data: dict


class BulkSyncRequest(BaseModel):
    """Schemat żądania bulk sync"""
    user_id: str
    topics: List[TopicBase] = []
    sessions: List[SessionBase] = []


class BulkSyncItemResult(BaseModel):
    """Wynik dla pojedynczego item w bulk sync"""
    id: str
    type: Literal["topic", "session"]
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

def db_topic_to_response(db_topic: SessionTopic) -> TopicResponse:
    """Konwertuj model DB tematu na response schema"""
    return TopicResponse(
        server_id=str(db_topic.id),  # Konwersja UUID → string
        local_id=db_topic.local_id,
        user_id=str(db_topic.user_id),  # Konwersja UUID → string
        name=db_topic.name,
        color=db_topic.color,
        icon=db_topic.icon,
        description=db_topic.description,
        total_sessions=db_topic.total_sessions,
        total_work_time=db_topic.total_work_time,
        total_break_time=db_topic.total_break_time,
        sort_order=db_topic.sort_order,
        is_active=db_topic.is_active,
        is_favorite=db_topic.is_favorite,
        created_at=db_topic.created_at,
        updated_at=db_topic.updated_at,
        synced_at=db_topic.synced_at,
        deleted_at=db_topic.deleted_at,
        version=db_topic.version,
        last_modified=db_topic.updated_at
    )


def db_session_to_response(db_session: SessionLog) -> SessionResponse:
    """Konwertuj model DB sesji na response schema"""
    return SessionResponse(
        server_id=str(db_session.id),  # Konwersja UUID → string
        local_id=db_session.local_id,
        user_id=str(db_session.user_id),  # Konwersja UUID → string
        topic_id=str(db_session.topic_id) if db_session.topic_id else None,
        session_date=db_session.session_date,
        started_at=db_session.started_at,
        ended_at=db_session.ended_at,
        work_duration=db_session.work_duration,
        short_break_duration=db_session.short_break_duration,
        long_break_duration=db_session.long_break_duration,
        actual_work_time=db_session.actual_work_time,
        actual_break_time=db_session.actual_break_time,
        session_type=db_session.session_type,
        status=db_session.status,
        pomodoro_count=db_session.pomodoro_count,
        notes=db_session.notes,
        tags=db_session.tags,
        productivity_rating=db_session.productivity_rating,
        created_at=db_session.created_at,
        updated_at=db_session.updated_at,
        synced_at=db_session.synced_at,
        deleted_at=db_session.deleted_at,
        version=db_session.version,
        last_modified=db_session.updated_at
    )


# =============================================================================
# TOPICS ENDPOINTS
# =============================================================================

@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_200_OK)
async def upsert_topic(
    request: UpsertTopicRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Utwórz lub zaktualizuj temat sesji (upsert).
    
    Obsługuje:
    - Tworzenie nowego tematu
    - Aktualizację istniejącego
    - Wykrywanie konfliktów wersji (409)
    """
    try:
        user_id = current_user["user_id"]
        
        # Sprawdź czy temat już istnieje (po local_id + user_id) - ignoruj usunięte
        existing = db.query(SessionTopic).filter(
            SessionTopic.local_id == request.local_id,
            SessionTopic.user_id == user_id,
            SessionTopic.deleted_at.is_(None)
        ).first()
        
        if existing:
            # Update - sprawdź wersję
            if existing.version >= request.version:
                logger.warning(f"Version conflict for topic {request.local_id}: server={existing.version}, client={request.version}")
                
                server_response = db_topic_to_response(existing)
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
            existing.name = request.name
            existing.color = request.color
            existing.icon = request.icon
            existing.description = request.description
            existing.total_sessions = request.total_sessions
            existing.total_work_time = request.total_work_time
            existing.total_break_time = request.total_break_time
            existing.sort_order = request.sort_order
            existing.is_active = request.is_active
            existing.is_favorite = request.is_favorite
            existing.updated_at = datetime.utcnow()
            existing.synced_at = datetime.utcnow()
            existing.version = request.version + 1
            existing.deleted_at = None  # Undelete jeśli był soft deleted
            
            db.commit()
            db.refresh(existing)
            
            logger.info(f"Updated topic {request.local_id} for user {user_id}")
            return db_topic_to_response(existing)
        
        else:
            # Create nowego - generuj UUID dla server_id
            new_topic = SessionTopic(
                id=str(uuid.uuid4()),
                local_id=request.local_id,
                user_id=user_id,
                name=request.name,
                color=request.color,
                icon=request.icon,
                description=request.description,
                total_sessions=request.total_sessions,
                total_work_time=request.total_work_time,
                total_break_time=request.total_break_time,
                sort_order=request.sort_order,
                is_active=request.is_active,
                is_favorite=request.is_favorite,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                synced_at=datetime.utcnow(),
                version=request.version
            )
            
            db.add(new_topic)
            db.commit()
            db.refresh(new_topic)
            
            logger.info(f"Created topic {request.local_id} (server_id: {new_topic.id}) for user {user_id}")
            return db_topic_to_response(new_topic)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upsert_topic: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/topics/{topic_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_topic(
    topic_id: str,
    version: int = Query(..., description="Current version for conflict detection"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete tematu sesji.
    
    Parametry:
    - topic_id: ID tematu do usunięcia
    - version: Aktualna wersja (do kontroli konfliktów)
    """
    try:
        # Pobierz user_id z tokena
        user_id = current_user["user_id"]
        
        topic = db.query(SessionTopic).filter(
            SessionTopic.id == topic_id,
            SessionTopic.user_id == user_id
        ).first()
        
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Topic not found"
            )
        
        # Sprawdź wersję
        if topic.version != version:
            logger.warning(f"Version conflict on delete topic {topic_id}: server={topic.version}, client={version}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": "Version conflict detected",
                    "local_version": version,
                    "server_version": topic.version,
                    "server_data": db_topic_to_response(topic).model_dump(mode='json')
                }
            )
        
        # Soft delete
        topic.deleted_at = datetime.utcnow()
        topic.version += 1
        topic.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Soft deleted topic {topic_id} for user {user_id}")
        
        return DeleteResponse(
            message="Topic soft deleted successfully",
            id=topic_id,
            deleted_at=topic.deleted_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_topic: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# SESSIONS ENDPOINTS
# =============================================================================

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def upsert_session(
    request: UpsertSessionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Utwórz lub zaktualizuj log sesji Pomodoro (upsert).
    
    Obsługuje:
    - Tworzenie nowej sesji
    - Aktualizację istniejącej
    - Wykrywanie konfliktów wersji (409)
    """
    try:
        user_id = current_user["user_id"]
        
        # Sprawdź czy sesja już istnieje (po local_id + user_id) - ignoruj usunięte
        existing = db.query(SessionLog).filter(
            SessionLog.local_id == request.local_id,
            SessionLog.user_id == user_id,
            SessionLog.deleted_at.is_(None)
        ).first()
        
        if existing:
            # Update - sprawdź wersję
            if existing.version >= request.version:
                logger.warning(f"Version conflict for session {request.local_id}: server={existing.version}, client={request.version}")
                
                server_response = db_session_to_response(existing)
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
            
            # Update istniejącej
            existing.topic_id = request.topic_id
            existing.session_date = request.session_date
            existing.started_at = request.started_at
            existing.ended_at = request.ended_at
            existing.work_duration = request.work_duration
            existing.short_break_duration = request.short_break_duration
            existing.long_break_duration = request.long_break_duration
            existing.actual_work_time = request.actual_work_time
            existing.actual_break_time = request.actual_break_time
            existing.session_type = request.session_type
            existing.status = request.status
            existing.pomodoro_count = request.pomodoro_count
            existing.notes = request.notes
            existing.tags = request.tags
            existing.productivity_rating = request.productivity_rating
            existing.updated_at = datetime.utcnow()
            existing.synced_at = datetime.utcnow()
            existing.version = request.version + 1
            existing.deleted_at = None  # Undelete jeśli był soft deleted
            
            db.commit()
            db.refresh(existing)
            
            logger.info(f"Updated session {request.local_id} for user {user_id}")
            return db_session_to_response(existing)
        
        else:
            # Create nowej - generuj UUID dla server_id
            new_session = SessionLog(
                id=str(uuid.uuid4()),
                local_id=request.local_id,
                user_id=user_id,
                topic_id=request.topic_id,
                session_date=request.session_date,
                started_at=request.started_at,
                ended_at=request.ended_at,
                work_duration=request.work_duration,
                short_break_duration=request.short_break_duration,
                long_break_duration=request.long_break_duration,
                actual_work_time=request.actual_work_time,
                actual_break_time=request.actual_break_time,
                session_type=request.session_type,
                status=request.status,
                pomodoro_count=request.pomodoro_count,
                notes=request.notes,
                tags=request.tags,
                productivity_rating=request.productivity_rating,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                synced_at=datetime.utcnow(),
                version=request.version
            )
            
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            
            logger.info(f"Created session {request.local_id} (server_id: {new_session.id}) for user {user_id}")
            return db_session_to_response(new_session)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upsert_session: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.delete("/sessions/{session_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    version: int = Query(..., description="Current version for conflict detection"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Soft delete sesji Pomodoro.
    
    Parametry:
    - session_id: ID sesji do usunięcia
    - version: Aktualna wersja (do kontroli konfliktów)
    """
    try:
        # Pobierz user_id z tokena
        user_id = current_user["user_id"]
        
        session = db.query(SessionLog).filter(
            SessionLog.id == session_id,
            SessionLog.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Sprawdź wersję
        if session.version != version:
            logger.warning(f"Version conflict on delete session {session_id}: server={session.version}, client={version}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": "Version conflict detected",
                    "local_version": version,
                    "server_version": session.version,
                    "server_data": db_session_to_response(session).model_dump(mode='json')
                }
            )
        
        # Soft delete
        session.deleted_at = datetime.utcnow()
        session.version += 1
        session.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Soft deleted session {session_id} for user {user_id}")
        
        return DeleteResponse(
            message="Session soft deleted successfully",
            id=session_id,
            deleted_at=session.deleted_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_session: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# LIST & FETCH ENDPOINTS
# =============================================================================

@router.get("/all", response_model=AllDataResponse, status_code=status.HTTP_200_OK)
async def get_all_pomodoro_data(
    type: Optional[Literal["topic", "session"]] = Query(None, description="Filter by type"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Pobierz wszystkie dane Pomodoro użytkownika (tematy i sesje).
    
    Parametry:
    - type: Filtr typu - 'topic' lub 'session' (opcjonalne)
    """
    try:
        # Pobierz user_id z tokena
        user_id = current_user["user_id"]
        
        topics = []
        sessions = []
        
        # Pobierz tematy (jeśli nie filtrujemy tylko sesji)
        if type is None or type == "topic":
            topics_query = db.query(SessionTopic).filter(
                SessionTopic.user_id == user_id,
                SessionTopic.deleted_at.is_(None)
            ).order_by(SessionTopic.sort_order, SessionTopic.created_at.desc())
            
            topics = [db_topic_to_response(t) for t in topics_query.all()]
        
        # Pobierz sesje (jeśli nie filtrujemy tylko tematów)
        if type is None or type == "session":
            sessions_query = db.query(SessionLog).filter(
                SessionLog.user_id == user_id,
                SessionLog.deleted_at.is_(None)
            ).order_by(SessionLog.session_date.desc(), SessionLog.started_at.desc())
            
            sessions = [db_session_to_response(s) for s in sessions_query.all()]
        
        logger.info(f"Retrieved {len(topics)} topics and {len(sessions)} sessions for user {user_id}")
        
        return AllDataResponse(
            topics=topics,
            sessions=sessions,
            topics_count=len(topics),
            sessions_count=len(sessions)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_all_pomodoro_data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/topics", response_model=ListTopicsResponse, status_code=status.HTTP_200_OK)
async def get_topics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Pobierz wszystkie tematy sesji Pomodoro użytkownika.
    
    Jest to alias dla GET /all?type=topic dla wygody.
    """
    try:
        user_id = current_user["user_id"]
        
        topics_query = db.query(SessionTopic).filter(
            SessionTopic.user_id == user_id,
            SessionTopic.deleted_at.is_(None)
        ).order_by(SessionTopic.sort_order, SessionTopic.created_at.desc())
        
        topics = [db_topic_to_response(t) for t in topics_query.all()]
        
        logger.info(f"Retrieved {len(topics)} topics for user {user_id}")
        
        return ListTopicsResponse(
            topics=topics,
            count=len(topics)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/sessions", response_model=ListSessionsResponse, status_code=status.HTTP_200_OK)
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Pobierz wszystkie sesje Pomodoro użytkownika.
    
    Jest to alias dla GET /all?type=session dla wygody.
    """
    try:
        user_id = current_user["user_id"]
        
        sessions_query = db.query(SessionLog).filter(
            SessionLog.user_id == user_id,
            SessionLog.deleted_at.is_(None)
        ).order_by(SessionLog.session_date.desc(), SessionLog.started_at.desc())
        
        sessions = [db_session_to_response(s) for s in sessions_query.all()]
        
        logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
        
        return ListSessionsResponse(
            sessions=sessions,
            count=len(sessions)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# =============================================================================
# BULK SYNC ENDPOINT
# =============================================================================

@router.post("/bulk-sync", response_model=BulkSyncResponse, status_code=status.HTTP_200_OK)
async def bulk_sync_pomodoro(
    request: BulkSyncRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronizuj wiele elementów Pomodoro naraz (bulk operation).
    
    Przydatne przy initial sync lub periodic sync wielu zmian.
    Obsługuje zarówno tematy jak i sesje w jednym requescie.
    """
    try:
        # Weryfikacja uprawnień
        if request.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot sync data for other users"
            )
        
        results = []
        success_count = 0
        error_count = 0
        
        # Sync topics
        for topic_data in request.topics:
            try:
                # Konwertuj do UpsertTopicRequest
                topic_request = UpsertTopicRequest(
                    user_id=request.user_id,
                    **topic_data.model_dump()
                )
                
                # Reuse upsert logic
                existing = db.query(SessionTopic).filter(
                    SessionTopic.id == topic_request.id,
                    SessionTopic.user_id == topic_request.user_id
                ).first()
                
                if existing and existing.version >= topic_request.version:
                    # Conflict
                    results.append(BulkSyncItemResult(
                        id=topic_request.id,
                        type="topic",
                        status="conflict",
                        server_version=existing.version
                    ))
                    error_count += 1
                else:
                    # Success - create or update
                    if existing:
                        # Update logic (abbreviated)
                        existing.name = topic_request.name
                        existing.version = topic_request.version + 1
                        existing.updated_at = datetime.utcnow()
                        existing.synced_at = datetime.utcnow()
                    else:
                        new_topic = SessionTopic(
                            id=topic_request.id,
                            user_id=topic_request.user_id,
                            name=topic_request.name,
                            color=topic_request.color,
                            version=topic_request.version
                        )
                        db.add(new_topic)
                    
                    db.commit()
                    
                    results.append(BulkSyncItemResult(
                        id=topic_request.id,
                        type="topic",
                        status="success",
                        version=topic_request.version + 1 if existing else topic_request.version
                    ))
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Error syncing topic {topic_data.id}: {e}")
                results.append(BulkSyncItemResult(
                    id=topic_data.id,
                    type="topic",
                    status="error",
                    error=str(e)
                ))
                error_count += 1
        
        # Sync sessions (similar logic)
        for session_data in request.sessions:
            try:
                session_request = UpsertSessionRequest(
                    user_id=request.user_id,
                    **session_data.model_dump()
                )
                
                existing = db.query(SessionLog).filter(
                    SessionLog.id == session_request.id,
                    SessionLog.user_id == session_request.user_id
                ).first()
                
                if existing and existing.version >= session_request.version:
                    results.append(BulkSyncItemResult(
                        id=session_request.id,
                        type="session",
                        status="conflict",
                        server_version=existing.version
                    ))
                    error_count += 1
                else:
                    if existing:
                        existing.session_type = session_request.session_type
                        existing.version = session_request.version + 1
                        existing.updated_at = datetime.utcnow()
                        existing.synced_at = datetime.utcnow()
                    else:
                        new_session = SessionLog(
                            id=session_request.id,
                            user_id=session_request.user_id,
                            session_date=session_request.session_date,
                            started_at=session_request.started_at,
                            work_duration=session_request.work_duration,
                            session_type=session_request.session_type,
                            status=session_request.status,
                            version=session_request.version
                        )
                        db.add(new_session)
                    
                    db.commit()
                    
                    results.append(BulkSyncItemResult(
                        id=session_request.id,
                        type="session",
                        status="success",
                        version=session_request.version + 1 if existing else session_request.version
                    ))
                    success_count += 1
                    
            except Exception as e:
                logger.error(f"Error syncing session {session_data.id}: {e}")
                results.append(BulkSyncItemResult(
                    id=session_data.id,
                    type="session",
                    status="error",
                    error=str(e)
                ))
                error_count += 1
        
        logger.info(f"Bulk sync completed: {success_count} success, {error_count} errors")
        
        return BulkSyncResponse(
            results=results,
            success_count=success_count,
            error_count=error_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk_sync_pomodoro: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
