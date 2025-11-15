"""
FastAPI Router for TeamWork Module
Endpointy API dla modułu współpracy zespołowej z mechanizmami administracji
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List
from datetime import datetime
import os
from pathlib import Path

from .database import get_db, User
from .auth import get_current_user
from . import teamwork_models as models
from . import teamwork_schemas as schemas
from .backblaze_service import BackblazeService

router = APIRouter(
    prefix="/api/teamwork",
    tags=["TeamWork"]
)


# ============================================================================
# HELPER FUNCTIONS - Sprawdzanie uprawnień
# ============================================================================

def get_user_id(user) -> str:
    """
    Ekstrahuje user_id z obiektu current_user (może być dict lub obiekt User).
    """
    if isinstance(user, dict):
        # JWT decode zwraca dict z kluczem 'user_id', nie 'id'
        return user.get("user_id") or user.get("id")
    return user.id


def get_group_or_404(db: Session, group_id: int) -> models.WorkGroup:
    """Pobiera grupę lub zwraca 404"""
    group = db.query(models.WorkGroup).filter(models.WorkGroup.group_id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grupa o ID {group_id} nie istnieje"
        )
    return group


def check_group_owner(db: Session, group_id: int, user_id: str) -> bool:
    """Sprawdza, czy użytkownik jest właścicielem grupy"""
    member = db.query(models.GroupMember).filter(
        and_(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id,
            models.GroupMember.role == 'owner'
        )
    ).first()
    return member is not None


def check_group_membership(db: Session, group_id: int, user_id: str) -> bool:
    """Sprawdza, czy użytkownik jest członkiem grupy"""
    member = db.query(models.GroupMember).filter(
        and_(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id
        )
    ).first()
    return member is not None


def require_group_owner(db: Session, group_id: int, user_id: str):
    """Wymaga, aby użytkownik był właścicielem grupy - rzuca wyjątek jeśli nie jest"""
    if not check_group_owner(db, group_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień. Tylko właściciel grupy może wykonać tę operację."
        )


def require_group_membership(db: Session, group_id: int, user_id: str):
    """Wymaga, aby użytkownik był członkiem grupy"""
    if not check_group_membership(db, group_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak dostępu. Musisz być członkiem tej grupy."
        )


# ============================================================================
# GROUPS ENDPOINTS
# ============================================================================

@router.post("/groups", response_model=schemas.WorkGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group_data: schemas.WorkGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tworzy nową grupę roboczą.
    Twórca grupy automatycznie staje się jej właścicielem (owner).
    """
    user_id = get_user_id(current_user)
    
    # Tworzenie grupy
    new_group = models.WorkGroup(
        group_name=group_data.group_name,
        description=group_data.description,
        created_by=user_id
    )
    db.add(new_group)
    db.flush()  # Żeby uzyskać group_id
    
    # Dodanie twórcy jako właściciela grupy
    owner_membership = models.GroupMember(
        group_id=new_group.group_id,
        user_id=user_id,
        role='owner'
    )
    db.add(owner_member)
    db.commit()
    db.refresh(new_group)
    
    return new_group


@router.get("/groups", response_model=List[schemas.WorkGroupResponse])
def get_user_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pobiera listę wszystkich grup, do których należy zalogowany użytkownik.
    """
    user_id = get_user_id(current_user)
    
    # Debug logging
    print(f"[TeamWork GET /groups] current_user type: {type(current_user)}")
    print(f"[TeamWork GET /groups] current_user value: {current_user}")
    print(f"[TeamWork GET /groups] extracted user_id: {user_id}")
    
    # Pobierz grupy, w których użytkownik jest członkiem wraz z ich tematami
    user_groups = db.query(models.WorkGroup).join(
        models.GroupMember
    ).filter(
        models.GroupMember.user_id == user_id
    ).options(
        joinedload(models.WorkGroup.members),
        joinedload(models.WorkGroup.topics)
    ).all()
    
    print(f"[TeamWork GET /groups] found {len(user_groups)} groups")
    for g in user_groups:
        print(f"  - Group {g.group_id}: {g.group_name} with {len(g.topics)} topics")
    
    return user_groups


@router.get("/groups/{group_id}", response_model=schemas.WorkGroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pobiera szczegóły grupy.
    Wymaga członkostwa w grupie.
    """
    group = get_group_or_404(db, group_id)
    require_group_membership(db, group_id, get_user_id(current_user))
    
    return group


@router.put("/groups/{group_id}", response_model=schemas.WorkGroupResponse)
def update_group(
    group_id: int,
    group_data: schemas.WorkGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aktualizuje dane grupy.
    Wymaga uprawnień właściciela (owner).
    """
    group = get_group_or_404(db, group_id)
    require_group_owner(db, group_id, get_user_id(current_user))
    
    # Aktualizacja pól
    if group_data.group_name is not None:
        group.group_name = group_data.group_name
    if group_data.description is not None:
        group.description = group_data.description
    if group_data.is_active is not None:
        group.is_active = group_data.is_active
    
    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Usuwa grupę.
    Wymaga uprawnień właściciela (owner).
    Kasuje również wszystkie powiązane wątki, wiadomości i zadania (CASCADE).
    """
    group = get_group_or_404(db, group_id)
    require_group_owner(db, group_id, get_user_id(current_user))
    
    db.delete(group)
    db.commit()
    return None


# ============================================================================
# GROUP MEMBERS ENDPOINTS
# ============================================================================

@router.post("/groups/{group_id}/members", response_model=schemas.GroupMemberInfo, status_code=status.HTTP_201_CREATED)
def add_group_member(
    group_id: int,
    member_data: schemas.GroupMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dodaje nowego członka do grupy.
    Wymaga uprawnień właściciela (owner).
    Nowi członkowie są zawsze dodawani z rolą 'member'.
    """
    group = get_group_or_404(db, group_id)
    require_group_owner(db, group_id, get_user_id(current_user))
    
    # Sprawdź, czy użytkownik już nie jest członkiem
    existing_member = db.query(models.GroupMember).filter(
        and_(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == member_data.user_id
        )
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ten użytkownik już jest członkiem grupy"
        )
    
    # Dodaj nowego członka (zawsze jako 'member', nie 'owner')
    new_member = models.GroupMember(
        group_id=group_id,
        user_id=member_data.user_id,
        role='member'  # Wymuszamy rolę 'member' dla nowych członków
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    
    return new_member


@router.delete("/groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_group_member(
    group_id: int,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Usuwa członka z grupy.
    Wymaga uprawnień właściciela (owner).
    Właściciel nie może usunąć samego siebie (musi najpierw przekazać rolę).
    """
    group = get_group_or_404(db, group_id)
    require_group_owner(db, group_id, get_user_id(current_user))
    
    # Sprawdź, czy właściciel nie próbuje usunąć samego siebie
    if user_id == get_user_id(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie możesz usunąć samego siebie z grupy. Najpierw przekaż rolę właściciela innemu członkowi."
        )
    
    # Znajdź członka
    member = db.query(models.GroupMember).filter(
        and_(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == user_id
        )
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie jest członkiem tej grupy"
        )
    
    db.delete(member)
    db.commit()
    return None


@router.put("/groups/{group_id}/transfer-ownership", response_model=schemas.WorkGroupResponse)
def transfer_group_ownership(
    group_id: int,
    transfer_data: schemas.TransferOwnershipRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Przekazuje własność grupy innemu członkowi.
    Wymaga uprawnień właściciela (owner).
    Nowy właściciel musi być członkiem grupy.
    """
    group = get_group_or_404(db, group_id)
    require_group_owner(db, group_id, get_user_id(current_user))
    
    # Sprawdź, czy nowy właściciel jest członkiem grupy
    new_owner_member = db.query(models.GroupMember).filter(
        and_(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == transfer_data.new_owner_id
        )
    ).first()
    
    if not new_owner_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nowy właściciel musi być członkiem grupy"
        )
    
    if transfer_data.new_owner_id == get_user_id(current_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Już jesteś właścicielem tej grupy"
        )
    
    # Transakcja: zmiana ról
    # 1. Obecny owner -> member
    current_owner_member = db.query(models.GroupMember).filter(
        and_(
            models.GroupMember.group_id == group_id,
            models.GroupMember.user_id == get_user_id(current_user)
        )
    ).first()
    current_owner_member.role = 'member'
    
    # 2. Nowy owner
    new_owner_member.role = 'owner'
    
    db.commit()
    db.refresh(group)
    
    return group


# ============================================================================
# TOPICS ENDPOINTS
# ============================================================================

@router.post("/topics", response_model=schemas.TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(
    topic_data: schemas.TopicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tworzy nowy wątek w grupie.
    Wymaga członkostwa w grupie.
    """
    group = get_group_or_404(db, topic_data.group_id)
    require_group_membership(db, topic_data.group_id, get_user_id(current_user))
    
    print(f"[TeamWork CREATE TOPIC] topic_name={topic_data.topic_name}, initial_message={topic_data.initial_message}")
    
    new_topic = models.Topic(
        group_id=topic_data.group_id,
        topic_name=topic_data.topic_name,
        created_by=get_user_id(current_user)
    )
    db.add(new_topic)
    db.flush()
    
    print(f"[TeamWork CREATE TOPIC] Created topic with ID={new_topic.topic_id}")
    
    # Opcjonalnie: dodaj pierwszą wiadomość
    if topic_data.initial_message:
        initial_msg = models.Message(
            topic_id=new_topic.topic_id,
            user_id=get_user_id(current_user),
            content=topic_data.initial_message
        )
        db.add(initial_msg)
        print(f"[TeamWork CREATE TOPIC] Added initial message: '{topic_data.initial_message[:50]}...'")
    else:
        print(f"[TeamWork CREATE TOPIC] No initial_message provided")
    
    db.commit()
    db.refresh(new_topic)
    
    print(f"[TeamWork CREATE TOPIC] Topic committed, returning response")
    
    return new_topic


@router.get("/groups/{group_id}/topics", response_model=List[schemas.TopicResponse])
def get_group_topics(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pobiera listę wątków w grupie.
    Wymaga członkostwa w grupie.
    """
    group = get_group_or_404(db, group_id)
    require_group_membership(db, group_id, get_user_id(current_user))
    
    topics = db.query(models.Topic).filter(
        models.Topic.group_id == group_id
    ).all()
    
    return topics


# ============================================================================
# MESSAGES ENDPOINTS
# ============================================================================

@router.post("/messages", response_model=schemas.MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dodaje nową wiadomość do wątku.
    Wymaga członkostwa w grupie, do której należy wątek.
    """
    # Pobierz wątek
    topic = db.query(models.Topic).filter(
        models.Topic.topic_id == message_data.topic_id
    ).first()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie istnieje"
        )
    
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    new_message = models.Message(
        topic_id=message_data.topic_id,
        user_id=get_user_id(current_user),
        content=message_data.content,
        background_color=message_data.background_color,
        is_important=message_data.is_important
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return new_message


@router.get("/topics/{topic_id}/messages", response_model=List[schemas.MessageResponse])
def get_topic_messages(
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pobiera wszystkie wiadomości z wątku.
    Wymaga członkostwa w grupie.
    """
    topic = db.query(models.Topic).filter(
        models.Topic.topic_id == topic_id
    ).first()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie istnieje"
        )
    
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    messages = db.query(models.Message).filter(
        models.Message.topic_id == topic_id
    ).order_by(models.Message.created_at.asc()).all()
    
    return messages


@router.patch("/messages/{message_id}", response_model=schemas.MessageResponse)
def update_message(
    message_id: int,
    message_data: schemas.MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aktualizuje wiadomość (tylko autor lub owner grupy).
    """
    message = db.query(models.Message).filter(
        models.Message.message_id == message_id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wiadomość nie istnieje"
        )
    
    # Pobierz wątek i sprawdź członkostwo
    topic = db.query(models.Topic).filter(
        models.Topic.topic_id == message.topic_id
    ).first()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie istnieje"
        )
    
    user_id = get_user_id(current_user)
    require_group_membership(db, topic.group_id, user_id)
    
    # Tylko autor może edytować (lub owner grupy - można dodać później)
    if message.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień do edycji tej wiadomości"
        )
    
    # Aktualizuj pola
    if message_data.content is not None:
        message.content = message_data.content
    if message_data.background_color is not None:
        message.background_color = message_data.background_color
    if message_data.is_important is not None:
        message.is_important = message_data.is_important
    
    db.commit()
    db.refresh(message)
    
    return message


# ============================================================================
# TASKS ENDPOINTS
# ============================================================================

@router.post("/tasks", response_model=schemas.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Tworzy nowe zadanie w wątku.
    Wymaga członkostwa w grupie.
    """
    topic = db.query(models.Topic).filter(
        models.Topic.topic_id == task_data.topic_id
    ).first()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie istnieje"
        )
    
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    new_task = models.TeamWorkTask(
        topic_id=task_data.topic_id,
        task_subject=task_data.task_subject,
        task_description=task_data.task_description,
        assigned_to=task_data.assigned_to,
        created_by=get_user_id(current_user),
        due_date=task_data.due_date,
        is_important=task_data.is_important
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return new_task


@router.get("/topics/{topic_id}/tasks", response_model=List[schemas.TaskResponse])
def get_topic_tasks(
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pobiera wszystkie zadania z wątku.
    Wymaga członkostwa w grupie.
    """
    topic = db.query(models.Topic).filter(
        models.Topic.topic_id == topic_id
    ).first()
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wątek nie istnieje"
        )
    
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    tasks = db.query(models.TeamWorkTask).filter(
        models.TeamWorkTask.topic_id == topic_id
    ).order_by(models.TeamWorkTask.created_at.desc()).all()
    
    return tasks


@router.patch("/tasks/{task_id}/complete", response_model=schemas.TaskResponse)
def mark_task_complete(
    task_id: int,
    complete_data: schemas.TaskCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Oznacza zadanie jako ukończone lub nieukończone.
    Wymaga członkostwa w grupie.
    """
    task = db.query(models.TeamWorkTask).filter(
        models.TeamWorkTask.task_id == task_id
    ).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zadanie nie istnieje"
        )
    
    # Pobierz wątek, aby sprawdzić członkostwo w grupie
    topic = db.query(models.Topic).filter(
        models.Topic.topic_id == task.topic_id
    ).first()
    
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    task.completed = complete_data.completed
    
    if complete_data.completed:
        task.completed_by = get_user_id(current_user)
        task.completed_at = datetime.now()
    else:
        task.completed_by = None
        task.completed_at = None
    
    db.commit()
    db.refresh(task)
    
    return task


# ============================================================================
# TOPIC FILES ENDPOINTS - Obsługa plików w wątkach (Backblaze B2)
# ============================================================================

@router.post("/topics/{topic_id}/files", response_model=schemas.TopicFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file_to_topic(
    topic_id: int,
    file: UploadFile = File(...),
    is_important: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload pliku do wątku tematycznego (Backblaze B2)
    
    Wymagania:
    - Użytkownik musi być członkiem grupy
    - Plik zostanie przesłany do Backblaze B2
    - Metadane zostaną zapisane w bazie danych
    """
    # Sprawdź czy topic istnieje
    topic = db.query(models.Topic).filter(models.Topic.topic_id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wątek o ID {topic_id} nie istnieje"
        )
    
    # Sprawdź członkostwo w grupie
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    # Inicjalizuj BackblazeService
    b2_service = BackblazeService()
    
    try:
        # Przeczytaj zawartość pliku
        file_content = await file.read()
        
        # Wygeneruj unikalną nazwę pliku w B2 (folder: teamwork/group_{group_id}/topic_{topic_id}/)
        b2_folder = f"teamwork/group_{topic.group_id}/topic_{topic_id}"
        original_filename = file.filename or "unnamed_file"
        
        # Upload do Backblaze B2
        upload_result = b2_service.upload_file(
            file_content=file_content,
            file_name=original_filename,
            content_type=file.content_type or "application/octet-stream",
            folder=b2_folder
        )
        
        # Stwórz rekord w bazie danych
        new_file = models.TopicFile(
            topic_id=topic_id,
            file_name=original_filename,
            file_size=len(file_content),
            content_type=file.content_type or "application/octet-stream",
            b2_file_id=upload_result['fileId'],
            b2_file_name=upload_result['fileName'],
            download_url=upload_result.get('downloadUrl', ''),
            uploaded_by=get_user_id(current_user),
            is_important=is_important
        )
        
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        
        return new_file
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas uploadu pliku: {str(e)}"
        )


@router.get("/topics/{topic_id}/files", response_model=List[schemas.TopicFileResponse])
def get_topic_files(
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Pobierz listę plików w wątku
    
    Wymagania:
    - Użytkownik musi być członkiem grupy
    """
    # Sprawdź czy topic istnieje
    topic = db.query(models.Topic).filter(models.Topic.topic_id == topic_id).first()
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wątek o ID {topic_id} nie istnieje"
        )
    
    # Sprawdź członkostwo
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    # Pobierz pliki
    files = db.query(models.TopicFile).filter(
        models.TopicFile.topic_id == topic_id
    ).order_by(models.TopicFile.uploaded_at.desc()).all()
    
    return files


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Usuń plik z wątku (usuwa z B2 i z bazy danych)
    
    Wymagania:
    - Użytkownik musi być właścicielem grupy LUB autorem pliku
    """
    # Pobierz plik
    file_record = db.query(models.TopicFile).filter(models.TopicFile.file_id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plik o ID {file_id} nie istnieje"
        )
    
    # Pobierz topic i grupę
    topic = db.query(models.Topic).filter(models.Topic.topic_id == file_record.topic_id).first()
    
    # Sprawdź uprawnienia: właściciel grupy LUB autor pliku
    is_owner = check_group_owner(db, topic.group_id, get_user_id(current_user))
    is_author = file_record.uploaded_by == get_user_id(current_user)
    
    if not (is_owner or is_author):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tylko właściciel grupy lub autor pliku może go usunąć"
        )
    
    # Usuń z Backblaze B2
    b2_service = BackblazeService()
    try:
        b2_service.delete_file(file_record.b2_file_id, file_record.b2_file_name)
    except Exception as e:
        # Loguj błąd, ale kontynuuj usuwanie z DB
        print(f"Błąd podczas usuwania pliku z B2: {str(e)}")
    
    # Usuń z bazy danych
    db.delete(file_record)
    db.commit()
    
    return None


@router.patch("/files/{file_id}", response_model=schemas.TopicFileResponse)
def update_file_metadata(
    file_id: int,
    update_data: schemas.TopicFileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aktualizuj metadane pliku (np. is_important)
    
    Wymagania:
    - Użytkownik musi być członkiem grupy
    """
    # Pobierz plik
    file_record = db.query(models.TopicFile).filter(models.TopicFile.file_id == file_id).first()
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plik o ID {file_id} nie istnieje"
        )
    
    # Pobierz topic i sprawdź członkostwo
    topic = db.query(models.Topic).filter(models.Topic.topic_id == file_record.topic_id).first()
    require_group_membership(db, topic.group_id, get_user_id(current_user))
    
    # Aktualizuj tylko is_important
    if update_data.is_important is not None:
        file_record.is_important = update_data.is_important
    
    db.commit()
    db.refresh(file_record)
    
    return file_record


