"""
Notes Router - REST API endpoints dla synchronizacji notatek
WebSocket endpoint dla real-time updates
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import json

from .database import get_db
from .auth import get_current_user, decode_token
from .notes_models import (
    Note, NoteLink,
    NoteCreate, NoteUpdate, NoteResponse, NoteLinkResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])

# WebSocket connection manager
class ConnectionManager:
    """Zarządza połączeniami WebSocket dla real-time updates"""
    
    def __init__(self):
        # Dict: user_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Dodaje nowe połączenie WebSocket"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Usuwa połączenie WebSocket"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Usuń user_id jeśli brak połączeń
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def broadcast_to_user(self, user_id: str, message: dict):
        """Wysyła wiadomość do wszystkich połączeń danego użytkownika"""
        if user_id not in self.active_connections:
            return
        
        message_json = json.dumps(message)
        
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")

# Global connection manager
ws_manager = ConnectionManager()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def convert_to_response(note: Note) -> NoteResponse:
    """Konwertuje SQLAlchemy Note model do Pydantic response"""
    return NoteResponse(
        id=str(note.id),
        user_id=str(note.user_id),
        parent_id=str(note.parent_id) if note.parent_id else None,
        title=note.title,
        content=note.content,
        color=note.color,
        version=note.version,
        synced_at=note.synced_at,
        created_at=note.created_at,
        updated_at=note.updated_at
    )


async def broadcast_to_user(user_id: str, event_type: str, data: dict):
    """Wysyła event WebSocket do użytkownika"""
    message = {
        "type": event_type,
        "data": data
    }
    await ws_manager.broadcast_to_user(user_id, message)


# =============================================================================
# REST API ENDPOINTS
# =============================================================================

@router.post("/sync", response_model=NoteResponse)
async def sync_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Synchronizuje notatkę (create lub update)
    
    - Jeśli notatka z local_id już istnieje → UPDATE
    - Jeśli nie istnieje → CREATE
    """
    try:
        # Sprawdź czy notatka już istnieje (po local_id lub id)
        existing_note = db.query(Note).filter(
            Note.user_id == current_user["user_id"],
            Note.id == note_data.local_id
        ).first()
        
        if existing_note:
            # UPDATE - conflict resolution (last-write-wins)
            existing_note.title = note_data.title
            existing_note.content = note_data.content
            existing_note.color = note_data.color
            existing_note.parent_id = note_data.parent_id
            existing_note.version = note_data.version + 1
            existing_note.synced_at = note_data.synced_at
            
            db.commit()
            db.refresh(existing_note)
            
            logger.info(f"Note updated: {existing_note.id}")
            
            # Broadcast update event
            await broadcast_to_user(
                str(current_user["user_id"]),
                "note_updated",
                convert_to_response(existing_note).model_dump(mode='json')
            )
            
            return convert_to_response(existing_note)
        
        else:
            # CREATE
            new_note = Note(
                id=note_data.local_id,
                user_id=current_user["user_id"],
                parent_id=note_data.parent_id,
                title=note_data.title,
                content=note_data.content,
                color=note_data.color,
                version=note_data.version or 1
            )
            
            db.add(new_note)
            db.commit()
            db.refresh(new_note)
            
            logger.info(f"Note created: {new_note.id}")
            
            # Broadcast create event
            await broadcast_to_user(
                str(current_user["user_id"]),
                "note_created",
                convert_to_response(new_note).model_dump(mode='json')
            )
            
            return convert_to_response(new_note)
    
    except Exception as e:
        logger.error(f"Error syncing note: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pobiera pojedynczą notatkę"""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user["user_id"]
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return convert_to_response(note)


@router.get("/user/{user_id}", response_model=List[NoteResponse])
async def get_user_notes(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pobiera wszystkie notatki użytkownika"""
    # Sprawdź autoryzację
    if str(current_user["user_id"]) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    notes = db.query(Note).filter(
        Note.user_id == user_id
    ).order_by(Note.created_at.desc()).all()
    
    return [convert_to_response(note) for note in notes]


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Usuwa notatkę"""
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == current_user["user_id"]
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db.delete(note)
    db.commit()
    
    logger.info(f"Note deleted: {note_id}")
    
    # Broadcast delete event
    await broadcast_to_user(
        str(current_user["user_id"]),
        "note_deleted",
        {"id": note_id}
    )
    
    return {"status": "deleted", "id": note_id}


# =============================================================================
# NOTE LINKS ENDPOINTS
# =============================================================================

@router.post("/links/sync", response_model=NoteLinkResponse)
async def sync_note_link(
    link_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Synchronizuje link między notatkami"""
    try:
        # Sprawdź czy link już istnieje
        existing_link = db.query(NoteLink).filter(
            NoteLink.id == link_data["local_id"]
        ).first()
        
        if existing_link:
            # UPDATE
            existing_link.source_note_id = link_data["source_note_id"]
            existing_link.target_note_id = link_data["target_note_id"]
            existing_link.link_text = link_data["link_text"]
            existing_link.start_position = link_data["start_position"]
            existing_link.end_position = link_data["end_position"]
            
            db.commit()
            db.refresh(existing_link)
            
            return NoteLinkResponse.model_validate(existing_link)
        
        else:
            # CREATE
            new_link = NoteLink(
                id=link_data["local_id"],
                source_note_id=link_data["source_note_id"],
                target_note_id=link_data["target_note_id"],
                link_text=link_data["link_text"],
                start_position=link_data["start_position"],
                end_position=link_data["end_position"]
            )
            
            db.add(new_link)
            db.commit()
            db.refresh(new_link)
            
            # Broadcast link created event
            await broadcast_to_user(
                str(current_user["user_id"]),
                "note_link_created",
                NoteLinkResponse.model_validate(new_link).model_dump(mode='json')
            )
            
            return NoteLinkResponse.model_validate(new_link)
    
    except Exception as e:
        logger.error(f"Error syncing link: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/links/note/{note_id}", response_model=List[NoteLinkResponse])
async def get_note_links(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pobiera wszystkie linki dla danej notatki"""
    links = db.query(NoteLink).filter(
        NoteLink.source_note_id == note_id
    ).all()
    
    return [NoteLinkResponse.model_validate(link) for link in links]


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(...)
):
    """
    WebSocket endpoint dla real-time updates
    
    URL: ws://localhost:8000/api/v1/notes/ws/{user_id}?token=YOUR_JWT_TOKEN
    
    Query Parameters:
        token: JWT access token dla autentykacji
    """
    # Autentykacja PRZED akceptacją WebSocket
    try:
        payload = decode_token(token)
        token_user_id = payload.get("user_id") or payload.get("sub")
        
        if not token_user_id or str(token_user_id) != str(user_id):
            logger.warning(f"WebSocket auth failed: token user_id={token_user_id}, path user_id={user_id}")
            # NIE wywołujemy websocket.close() - po prostu nie akceptujemy połączenia
            return
            
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        # NIE wywołujemy websocket.close() - po prostu nie akceptujemy połączenia
        return
    
    # Token OK - teraz możemy zaakceptować połączenie
    try:
        # Połącz WebSocket (acceptuje połączenie)
        await ws_manager.connect(websocket, user_id)
        logger.info(f"✅ WebSocket connected for user {user_id}")
        
        while True:
            # Odbierz wiadomość od klienta
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Obsłuż ping/pong
                if message_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
                # Inne typy wiadomości można obsłużyć tutaj
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, user_id)

