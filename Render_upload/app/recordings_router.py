"""
CallCryptor Recordings Router for PRO-Ka-Po API
==================================================

Endpointy do synchronizacji nagrań CallCryptor (TYLKO metadane).
Privacy-first: pliki audio NIE są synchronizowane!

Architektura:
- Local-first: SQLite primary, PostgreSQL backup
- Last-Write-Wins conflict resolution
- Soft delete (deleted_at timestamp)
- Bulk sync max 100 recordings
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from loguru import logger

from .database import get_db
from .auth import get_current_user
from .recordings_orm import RecordingSource, Recording, RecordingTag
from .recordings_models import (
    RecordingSourceCreate,
    RecordingSourceUpdate,
    RecordingSourceResponse,
    RecordingCreate,
    RecordingUpdate,
    RecordingResponse,
    RecordingTagCreate,
    RecordingTagUpdate,
    RecordingTagResponse,
    BulkSyncRequest,
    BulkSyncResponse,
    RecordingSyncItem,
    SyncStatsResponse
)

router = APIRouter(prefix="/api/recordings", tags=["CallCryptor Recordings"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_recording_from_db(db: Session, recording_id: UUID, user_id: UUID):
    """Pobierz nagranie z bazy (including soft-deleted)"""
    query = text("""
        SELECT * FROM s07_callcryptor.recordings
        WHERE id = :recording_id AND user_id = :user_id
    """)
    result = db.execute(query, {"recording_id": str(recording_id), "user_id": str(user_id)})
    return result.mappings().first()


def get_source_from_db(db: Session, source_id: UUID, user_id: UUID):
    """Pobierz źródło z bazy (including soft-deleted)"""
    query = text("""
        SELECT * FROM s07_callcryptor.recording_sources
        WHERE id = :source_id AND user_id = :user_id
    """)
    result = db.execute(query, {"source_id": str(source_id), "user_id": str(user_id)})
    return result.mappings().first()


def get_tag_from_db(db: Session, tag_id: UUID, user_id: UUID):
    """Pobierz tag z bazy (including soft-deleted)"""
    query = text("""
        SELECT * FROM s07_callcryptor.recording_tags
        WHERE id = :tag_id AND user_id = :user_id
    """)
    result = db.execute(query, {"tag_id": str(tag_id), "user_id": str(user_id)})
    return result.mappings().first()


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "callcryptor-recordings",
        "timestamp": datetime.utcnow().isoformat(),
        "privacy": "files_not_synced"
    }


# =============================================================================
# RECORDING SOURCES ENDPOINTS
# =============================================================================

@router.post("/sources", response_model=RecordingSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    request: RecordingSourceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Utwórz nowe źródło nagrań"""
    try:
        user_id = current_user["user_id"]
        
        # Konwertuj file_extensions na JSONB
        if request.file_extensions:
            extensions_json = '[' + ','.join([f'"{ext}"' for ext in request.file_extensions]) + ']'
        else:
            extensions_json = '[]'
        
        query = text("""
            INSERT INTO s07_callcryptor.recording_sources (
                user_id, source_name, source_type, folder_path, file_extensions,
                scan_depth, email_account_id, search_phrase, search_type,
                search_all_folders, target_folder, attachment_pattern,
                contact_ignore_words, is_active, last_scan_at, recordings_count
            ) VALUES (
                :user_id, :source_name, :source_type, :folder_path, :file_extensions::jsonb,
                :scan_depth, :email_account_id, :search_phrase, :search_type,
                :search_all_folders, :target_folder, :attachment_pattern,
                :contact_ignore_words, :is_active, :last_scan_at, :recordings_count
            ) RETURNING *
        """)
        
        result = db.execute(query, {
            "user_id": user_id,
            "source_name": request.source_name,
            "source_type": request.source_type,
            "folder_path": request.folder_path,
            "file_extensions": extensions_json,
            "scan_depth": request.scan_depth,
            "email_account_id": request.email_account_id,
            "search_phrase": request.search_phrase,
            "search_type": request.search_type,
            "search_all_folders": request.search_all_folders,
            "target_folder": request.target_folder,
            "attachment_pattern": request.attachment_pattern,
            "contact_ignore_words": request.contact_ignore_words,
            "is_active": request.is_active,
            "last_scan_at": request.last_scan_at,
            "recordings_count": request.recordings_count
        })
        db.commit()
        
        row = result.mappings().first()
        return RecordingSourceResponse(**dict(row))
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating recording source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create source: {str(e)}"
        )


@router.get("/sources", response_model=List[RecordingSourceResponse])
async def list_sources(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lista źródeł nagrań użytkownika"""
    try:
        user_id = current_user["user_id"]
        
        deleted_condition = "" if include_deleted else "AND deleted_at IS NULL"
        
        query = text(f"""
            SELECT * FROM s07_callcryptor.recording_sources
            WHERE user_id = :user_id {deleted_condition}
            ORDER BY created_at DESC
        """)
        
        result = db.execute(query, {"user_id": user_id})
        sources = [RecordingSourceResponse(**dict(row)) for row in result.mappings()]
        return sources
        
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sources: {str(e)}"
        )


@router.put("/sources/{source_id}", response_model=RecordingSourceResponse)
async def update_source(
    source_id: UUID,
    request: RecordingSourceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Zaktualizuj źródło nagrań"""
    try:
        user_id = current_user["user_id"]
        
        # Sprawdź czy źródło istnieje
        source = get_source_from_db(db, source_id, UUID(user_id))
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        # Build update query dynamically
        updates = []
        params = {"source_id": str(source_id), "user_id": user_id}
        
        if request.source_name is not None:
            updates.append("source_name = :source_name")
            params["source_name"] = request.source_name
        if request.is_active is not None:
            updates.append("is_active = :is_active")
            params["is_active"] = request.is_active
        if request.folder_path is not None:
            updates.append("folder_path = :folder_path")
            params["folder_path"] = request.folder_path
        if request.recordings_count is not None:
            updates.append("recordings_count = :recordings_count")
            params["recordings_count"] = request.recordings_count
        
        if not updates:
            # Nic do aktualizacji, zwróć source bez zmian
            return RecordingSourceResponse(**dict(source))
        
        updates.append("version = version + 1")
        update_clause = ", ".join(updates)
        
        query = text(f"""
            UPDATE s07_callcryptor.recording_sources
            SET {update_clause}
            WHERE id = :source_id AND user_id = :user_id
            RETURNING *
        """)
        
        result = db.execute(query, params)
        db.commit()
        
        row = result.mappings().first()
        return RecordingSourceResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update source: {str(e)}"
        )


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: UUID,
    hard_delete: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Usuń źródło nagrań (soft delete domyślnie)"""
    try:
        user_id = current_user["user_id"]
        
        # Sprawdź czy źródło istnieje
        source = get_source_from_db(db, source_id, UUID(user_id))
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        if hard_delete:
            # Hard delete - usuń z bazy
            query = text("""
                DELETE FROM s07_callcryptor.recording_sources
                WHERE id = :source_id AND user_id = :user_id
            """)
        else:
            # Soft delete - ustaw deleted_at
            query = text("""
                UPDATE s07_callcryptor.recording_sources
                SET deleted_at = NOW(), version = version + 1
                WHERE id = :source_id AND user_id = :user_id
            """)
        
        db.execute(query, {"source_id": str(source_id), "user_id": user_id})
        db.commit()
        
        return {
            "message": "Source deleted successfully",
            "id": str(source_id),
            "hard_delete": hard_delete
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete source: {str(e)}"
        )


# =============================================================================
# RECORDINGS ENDPOINTS
# =============================================================================

@router.post("/", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED)
async def create_recording(
    request: RecordingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Utwórz nowe nagranie (TYLKO metadane, bez pliku audio!)"""
    try:
        user_id = current_user["user_id"]
        
        # Konwertuj lists/dicts na JSONB
        tags_json = '[' + ','.join([f'"{tag}"' for tag in request.tags]) + ']' if request.tags else '[]'
        ai_tasks_json = str(request.ai_summary_tasks).replace("'", '"') if request.ai_summary_tasks else None
        ai_points_json = '[' + ','.join([f'"{p}"' for p in request.ai_key_points]) + ']' if request.ai_key_points else None
        ai_actions_json = str(request.ai_action_items).replace("'", '"') if request.ai_action_items else None
        
        query = text("""
            INSERT INTO s07_callcryptor.recordings (
                user_id, source_id, file_name, file_size, file_hash,
                email_message_id, email_subject, email_sender,
                contact_name, contact_phone, duration, recording_date,
                tags, notes, transcription_status, transcription_text,
                transcription_language, transcription_confidence, transcription_date,
                transcription_error, ai_summary_status, ai_summary_text,
                ai_summary_date, ai_summary_error, ai_summary_tasks,
                ai_key_points, ai_action_items, note_id, task_id,
                is_archived, archived_at, archive_reason, is_favorite, favorited_at
            ) VALUES (
                :user_id, :source_id, :file_name, :file_size, :file_hash,
                :email_message_id, :email_subject, :email_sender,
                :contact_name, :contact_phone, :duration, :recording_date,
                :tags::jsonb, :notes, :transcription_status, :transcription_text,
                :transcription_language, :transcription_confidence, :transcription_date,
                :transcription_error, :ai_summary_status, :ai_summary_text,
                :ai_summary_date, :ai_summary_error, :ai_summary_tasks::jsonb,
                :ai_key_points::jsonb, :ai_action_items::jsonb, :note_id, :task_id,
                :is_archived, :archived_at, :archive_reason, :is_favorite, :favorited_at
            ) RETURNING *
        """)
        
        result = db.execute(query, {
            "user_id": user_id,
            "source_id": str(request.source_id),
            "file_name": request.file_name,
            "file_size": request.file_size,
            "file_hash": request.file_hash,
            "email_message_id": request.email_message_id,
            "email_subject": request.email_subject,
            "email_sender": request.email_sender,
            "contact_name": request.contact_name,
            "contact_phone": request.contact_phone,
            "duration": request.duration,
            "recording_date": request.recording_date,
            "tags": tags_json,
            "notes": request.notes,
            "transcription_status": request.transcription_status,
            "transcription_text": request.transcription_text,
            "transcription_language": request.transcription_language,
            "transcription_confidence": request.transcription_confidence,
            "transcription_date": request.transcription_date,
            "transcription_error": request.transcription_error,
            "ai_summary_status": request.ai_summary_status,
            "ai_summary_text": request.ai_summary_text,
            "ai_summary_date": request.ai_summary_date,
            "ai_summary_error": request.ai_summary_error,
            "ai_summary_tasks": ai_tasks_json,
            "ai_key_points": ai_points_json,
            "ai_action_items": ai_actions_json,
            "note_id": str(request.note_id) if request.note_id else None,
            "task_id": str(request.task_id) if request.task_id else None,
            "is_archived": request.is_archived,
            "archived_at": request.archived_at,
            "archive_reason": request.archive_reason,
            "is_favorite": request.is_favorite,
            "favorited_at": request.favorited_at
        })
        db.commit()
        
        row = result.mappings().first()
        return RecordingResponse(**dict(row))
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create recording: {str(e)}"
        )


@router.get("/", response_model=List[RecordingResponse])
async def list_recordings(
    source_id: Optional[UUID] = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Lista nagrań użytkownika"""
    try:
        user_id = current_user["user_id"]
        
        conditions = ["user_id = :user_id"]
        params = {"user_id": user_id, "limit": limit, "offset": offset}
        
        if source_id:
            conditions.append("source_id = :source_id")
            params["source_id"] = str(source_id)
        
        if not include_deleted:
            conditions.append("deleted_at IS NULL")
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT * FROM s07_callcryptor.recordings
            WHERE {where_clause}
            ORDER BY recording_date DESC NULLS LAST, created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.execute(query, params)
        recordings = [RecordingResponse(**dict(row)) for row in result.mappings()]
        return recordings
        
    except Exception as e:
        logger.error(f"Error listing recordings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list recordings: {str(e)}"
        )


@router.get("/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pobierz pojedyncze nagranie"""
    try:
        user_id = current_user["user_id"]
        
        recording = get_recording_from_db(db, recording_id, UUID(user_id))
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        return RecordingResponse(**dict(recording))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recording: {str(e)}"
        )


@router.put("/{recording_id}", response_model=RecordingResponse)
async def update_recording(
    recording_id: UUID,
    request: RecordingUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Zaktualizuj nagranie"""
    try:
        user_id = current_user["user_id"]
        
        # Sprawdź czy nagranie istnieje
        recording = get_recording_from_db(db, recording_id, UUID(user_id))
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        # Build update query dynamically
        updates = []
        params = {"recording_id": str(recording_id), "user_id": user_id}
        
        update_dict = request.model_dump(exclude_unset=True)
        
        for field, value in update_dict.items():
            if field == "tags" and value is not None:
                updates.append(f"{field} = :tags::jsonb")
                params["tags"] = '[' + ','.join([f'"{tag}"' for tag in value]) + ']'
            elif field in ["ai_summary_tasks", "ai_key_points", "ai_action_items"] and value is not None:
                updates.append(f"{field} = :{field}::jsonb")
                if isinstance(value, list) and value and isinstance(value[0], str):
                    params[field] = '[' + ','.join([f'"{v}"' for v in value]) + ']'
                else:
                    params[field] = str(value).replace("'", '"')
            else:
                updates.append(f"{field} = :{field}")
                params[field] = value
        
        if not updates:
            return RecordingResponse(**dict(recording))
        
        updates.append("version = version + 1")
        update_clause = ", ".join(updates)
        
        query = text(f"""
            UPDATE s07_callcryptor.recordings
            SET {update_clause}
            WHERE id = :recording_id AND user_id = :user_id
            RETURNING *
        """)
        
        result = db.execute(query, params)
        db.commit()
        
        row = result.mappings().first()
        return RecordingResponse(**dict(row))
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update recording: {str(e)}"
        )


@router.delete("/{recording_id}")
async def delete_recording(
    recording_id: UUID,
    hard_delete: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Usuń nagranie (soft delete domyślnie)"""
    try:
        user_id = current_user["user_id"]
        
        recording = get_recording_from_db(db, recording_id, UUID(user_id))
        if not recording:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recording not found"
            )
        
        if hard_delete:
            query = text("""
                DELETE FROM s07_callcryptor.recordings
                WHERE id = :recording_id AND user_id = :user_id
            """)
        else:
            query = text("""
                UPDATE s07_callcryptor.recordings
                SET deleted_at = NOW(), version = version + 1
                WHERE id = :recording_id AND user_id = :user_id
            """)
        
        db.execute(query, {"recording_id": str(recording_id), "user_id": user_id})
        db.commit()
        
        return {
            "message": "Recording deleted successfully",
            "id": str(recording_id),
            "hard_delete": hard_delete
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete recording: {str(e)}"
        )


# =============================================================================
# BULK SYNC ENDPOINT
# =============================================================================

@router.post("/bulk-sync", response_model=BulkSyncResponse)
async def bulk_sync(
    request: BulkSyncRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk synchronizacja nagrań (max 100 naraz)
    Last-Write-Wins conflict resolution
    """
    try:
        user_id = UUID(current_user["user_id"])
        
        recordings_created = 0
        recordings_updated = 0
        recordings_deleted = 0
        sources_created = 0
        sources_updated = 0
        tags_created = 0
        tags_updated = 0
        conflicts_resolved = 0

        # Walidacja: upewnij się, że wszystkie źródła istnieją lub zostały dostarczone w payloadzie
        requested_source_ids = {
            rec.source_id for rec in request.recordings if rec.source_id
        }
        payload_source_ids = {
            str(src.id) for src in (request.sources or [])
        }

        if requested_source_ids:
            existing_source_rows = db.query(RecordingSource.id).filter(
                RecordingSource.user_id == str(user_id),
                RecordingSource.id.in_(list(requested_source_ids))
            ).all()
            existing_source_ids = {row[0] for row in existing_source_rows}
        else:
            existing_source_ids = set()

        missing_source_ids = requested_source_ids - existing_source_ids - payload_source_ids
        if missing_source_ids:
            missing_ids_str = ", ".join(sorted(missing_source_ids))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Bulk sync payload is missing recording sources for ids: "
                    f"{missing_ids_str}. Send corresponding sources before"
                    " syncing recordings."
                )
            )
        
        # 1. Sync sources first
        if request.sources:
            for source in request.sources:
                source_id = str(source.id)
                existing = db.query(RecordingSource).filter(
                    RecordingSource.id == source_id,
                    RecordingSource.user_id == str(user_id)
                ).first()
                
                if not existing:
                    # Create new source
                    db_source = RecordingSource(
                        id=source_id,
                        user_id=str(user_id),
                        source_name=source.source_name,
                        source_type=source.source_type,
                        folder_path=source.folder_path,
                        file_extensions=source.file_extensions,
                        scan_depth=source.scan_depth,
                        email_account_id=source.email_account_id,
                        search_phrase=source.search_phrase,
                        search_type=source.search_type,
                        search_all_folders=source.search_all_folders,
                        target_folder=source.target_folder,
                        attachment_pattern=source.attachment_pattern,
                        contact_ignore_words=source.contact_ignore_words,
                        is_active=source.is_active,
                        last_scan_at=source.last_scan_at,
                        recordings_count=source.recordings_count,
                        created_at=source.created_at,
                        updated_at=source.updated_at,
                        deleted_at=source.deleted_at,
                        # REMOVED: synced_at - PostgreSQL doesn't have this field
                        version=source.version
                    )
                    db.add(db_source)
                    sources_created += 1
                else:
                    # Update if newer (Last-Write-Wins)
                    if source.updated_at > existing.updated_at:
                        previous_version = existing.version
                        existing.source_name = source.source_name
                        existing.source_type = source.source_type
                        existing.folder_path = source.folder_path
                        existing.file_extensions = source.file_extensions
                        existing.scan_depth = source.scan_depth
                        existing.email_account_id = source.email_account_id
                        existing.search_phrase = source.search_phrase
                        existing.search_type = source.search_type
                        existing.search_all_folders = source.search_all_folders
                        existing.target_folder = source.target_folder
                        existing.attachment_pattern = source.attachment_pattern
                        existing.contact_ignore_words = source.contact_ignore_words
                        existing.is_active = source.is_active
                        existing.last_scan_at = source.last_scan_at
                        existing.recordings_count = source.recordings_count
                        existing.updated_at = source.updated_at
                        existing.deleted_at = source.deleted_at
                        # REMOVED: synced_at - PostgreSQL doesn't have this field
                        existing.version = source.version
                        sources_updated += 1
                        if source.version != previous_version:
                            conflicts_resolved += 1

            # Upewnij się, że nowo dodane źródła są widoczne przed synchronizacją nagrań
            db.flush()
        
        # 2. Sync recordings
        for rec in request.recordings:
            existing = db.query(Recording).filter(
                Recording.id == rec.id,
                Recording.user_id == str(user_id)
            ).first()
            
            if not existing:
                # Create new recording
                db_recording = Recording(
                    id=rec.id,
                    user_id=str(user_id),
                    source_id=rec.source_id,
                    file_name=rec.file_name,
                    file_size=rec.file_size,
                    file_hash=rec.file_hash,
                    email_message_id=rec.email_message_id,
                    email_subject=rec.email_subject,
                    email_sender=rec.email_sender,
                    contact_name=rec.contact_name,
                    contact_phone=rec.contact_phone,
                    recording_date=rec.recording_date,
                    duration=rec.duration_seconds,  # FIXED: ORM uses 'duration' not 'duration_seconds'
                    tags=rec.tags,
                    notes=rec.notes,
                    # Transcription fields
                    transcription_status=rec.transcription_status,
                    transcription_text=rec.transcription_text,
                    transcription_language=rec.transcription_language,
                    transcription_confidence=rec.transcription_confidence,
                    transcription_date=rec.transcription_date,
                    transcription_error=rec.transcription_error,
                    # AI analysis
                    # REMOVED: ai_transcript - PostgreSQL doesn't have this field
                    ai_summary_text=rec.ai_summary,  # FIXED: ORM uses ai_summary_text, Pydantic uses ai_summary
                    ai_summary_status=rec.ai_summary_status,
                    ai_summary_date=rec.ai_summary_date,
                    ai_summary_error=rec.ai_summary_error,
                    ai_summary_tasks=rec.ai_summary_tasks,
                    ai_key_points=rec.ai_key_points,
                    ai_action_items=rec.ai_action_items,
                    # REMOVED: ai_sentiment, ai_language - PostgreSQL doesn't have these fields
                    # Archivization
                    is_archived=rec.is_archived,
                    archived_at=rec.archived_at,
                    archive_reason=rec.archive_reason,
                    # Favorites
                    is_favorite=rec.is_favorite,
                    favorited_at=rec.favorited_at,
                    # Links
                    task_id=rec.task_id,
                    # REMOVED: pomodoro_session_id - PostgreSQL doesn't have this field
                    note_id=rec.note_id,
                    # Sync metadata
                    created_at=rec.created_at,
                    updated_at=rec.updated_at,
                    deleted_at=rec.deleted_at,
                    # REMOVED: synced_at - PostgreSQL doesn't have this field
                    version=rec.version
                )
                db.add(db_recording)
                recordings_created += 1
            else:
                # Last-Write-Wins: porównaj updated_at
                if rec.deleted_at:
                    # Klient usunął nagranie
                    if not existing.deleted_at:
                        # Soft delete na serwerze
                        existing.deleted_at = rec.deleted_at
                        existing.updated_at = rec.updated_at
                        existing.version += 1
                        # REMOVED: synced_at - PostgreSQL doesn't have this field
                        recordings_deleted += 1
                elif rec.updated_at > existing.updated_at:
                    # Klient ma nowszą wersję - update serwera
                    existing.source_id = rec.source_id
                    existing.file_name = rec.file_name
                    existing.file_size = rec.file_size
                    existing.file_hash = rec.file_hash
                    existing.email_message_id = rec.email_message_id
                    existing.email_subject = rec.email_subject
                    existing.email_sender = rec.email_sender
                    existing.contact_name = rec.contact_name
                    existing.contact_phone = rec.contact_phone
                    existing.recording_date = rec.recording_date
                    existing.duration = rec.duration_seconds  # FIXED: ORM uses 'duration'
                    existing.tags = rec.tags
                    existing.notes = rec.notes
                    # Transcription fields
                    existing.transcription_status = rec.transcription_status
                    existing.transcription_text = rec.transcription_text
                    existing.transcription_language = rec.transcription_language
                    existing.transcription_confidence = rec.transcription_confidence
                    existing.transcription_date = rec.transcription_date
                    existing.transcription_error = rec.transcription_error
                    # AI analysis
                    # REMOVED: ai_transcript - PostgreSQL doesn't have this field
                    existing.ai_summary_text = rec.ai_summary  # FIXED: ORM uses ai_summary_text
                    existing.ai_summary_status = rec.ai_summary_status
                    existing.ai_summary_date = rec.ai_summary_date
                    existing.ai_summary_error = rec.ai_summary_error
                    existing.ai_summary_tasks = rec.ai_summary_tasks
                    existing.ai_key_points = rec.ai_key_points
                    existing.ai_action_items = rec.ai_action_items
                    # REMOVED: ai_sentiment, ai_language - PostgreSQL doesn't have these fields
                    # Archivization
                    existing.is_archived = rec.is_archived
                    existing.archived_at = rec.archived_at
                    existing.archive_reason = rec.archive_reason
                    # Favorites
                    existing.is_favorite = rec.is_favorite
                    existing.favorited_at = rec.favorited_at
                    # Links
                    existing.task_id = rec.task_id
                    # REMOVED: pomodoro_session_id - PostgreSQL doesn't have this field
                    existing.note_id = rec.note_id
                    # Sync metadata
                    existing.updated_at = rec.updated_at
                    # REMOVED: synced_at - PostgreSQL doesn't have this field
                    existing.version = rec.version
                    recordings_updated += 1
                    if rec.version != existing.version:
                        conflicts_resolved += 1
        
        # 3. Get server recordings changed since last_sync_at
        if request.last_sync_at:
            server_recs = db.query(Recording).filter(
                Recording.user_id == str(user_id),
                Recording.updated_at > request.last_sync_at
            ).order_by(Recording.updated_at.desc()).limit(100).all()
        else:
            # First sync - get all recordings
            server_recs = db.query(Recording).filter(
                Recording.user_id == str(user_id)
            ).order_by(Recording.updated_at.desc()).limit(100).all()
        
        # Convert ORM objects to RecordingSyncItem
        server_recordings = [
            RecordingSyncItem(
                id=r.id,
                source_id=r.source_id,
                file_name=r.file_name,
                file_size=r.file_size,
                file_hash=r.file_hash,
                email_message_id=r.email_message_id,
                email_subject=r.email_subject,
                email_sender=r.email_sender,
                contact_name=r.contact_name,
                contact_phone=r.contact_phone,
                recording_date=r.recording_date,
                duration_seconds=r.duration,  # FIXED: ORM uses 'duration', Pydantic uses 'duration_seconds'
                tags=r.tags,
                notes=r.notes,
                # Transcription
                transcription_status=r.transcription_status or "pending",
                transcription_text=r.transcription_text,
                transcription_language=r.transcription_language,
                transcription_confidence=r.transcription_confidence,
                transcription_date=r.transcription_date,
                transcription_error=r.transcription_error,
                # AI analysis
                # REMOVED: ai_transcript - PostgreSQL doesn't have this field
                ai_summary=r.ai_summary_text,  # FIXED: ORM uses ai_summary_text, Pydantic uses ai_summary
                ai_summary_status=r.ai_summary_status or "pending",
                ai_summary_date=r.ai_summary_date,
                ai_summary_error=r.ai_summary_error,
                ai_summary_tasks=r.ai_summary_tasks,
                ai_key_points=r.ai_key_points,
                ai_action_items=r.ai_action_items,
                # REMOVED: ai_sentiment, ai_language - PostgreSQL doesn't have these fields
                # Archivization
                is_archived=r.is_archived or False,
                archived_at=r.archived_at,
                archive_reason=r.archive_reason,
                # Favorites
                is_favorite=r.is_favorite or False,
                favorited_at=r.favorited_at,
                # Links
                task_id=r.task_id,
                # REMOVED: pomodoro_session_id - PostgreSQL doesn't have this field
                note_id=r.note_id,
                # Sync metadata
                created_at=r.created_at,
                updated_at=r.updated_at,
                deleted_at=r.deleted_at,
                # REMOVED: synced_at - PostgreSQL doesn't have this field
                version=r.version
            )
            for r in server_recs
        ]
        
        db.commit()
        
        return BulkSyncResponse(
            recordings_created=recordings_created,
            recordings_updated=recordings_updated,
            recordings_deleted=recordings_deleted,
            sources_created=sources_created,
            sources_updated=sources_updated,
            tags_created=tags_created,
            tags_updated=tags_updated,
            conflicts_resolved=conflicts_resolved,
            server_recordings=server_recordings,
            server_sources=[],  # TODO: implement
            server_tags=[],     # TODO: implement
            sync_timestamp=datetime.utcnow()
        )
        
    except HTTPException as exc:
        db.rollback()
        raise exc
    except Exception as e:
        db.rollback()
        logger.error(f"Error during bulk sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk sync failed: {str(e)}"
        )


# =============================================================================
# SYNC STATS
# =============================================================================

@router.get("/sync/stats", response_model=SyncStatsResponse)
async def get_sync_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Pobierz statystyki synchronizacji"""
    try:
        user_id = current_user["user_id"]
        
        # Count recordings (using ORM)
        total_recordings = db.query(Recording).filter(
            Recording.user_id == user_id,
            Recording.deleted_at.is_(None)
        ).count()
        
        # Count sources
        total_sources = db.query(RecordingSource).filter(
            RecordingSource.user_id == user_id,
            RecordingSource.deleted_at.is_(None)
        ).count()
        
        # Count tags
        total_tags = db.query(RecordingTag).filter(
            RecordingTag.user_id == user_id,
            RecordingTag.deleted_at.is_(None)
        ).count()
        
        return SyncStatsResponse(
            total_recordings=total_recordings or 0,
            total_sources=total_sources or 0,
            total_tags=total_tags or 0,
            last_sync_at=None,  # TODO: store last_sync_at
            pending_uploads=0,
            pending_downloads=0
        )
        
    except Exception as e:
        logger.error(f"Error getting sync stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync stats: {str(e)}"
        )
