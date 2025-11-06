"""
Tasks Router for PRO-Ka-Po API
Endpoints to sync Tasks & Kanban in local-first architecture
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional, List
from datetime import datetime
from loguru import logger
import asyncio

from .database import get_db
from .auth import get_current_user, decode_token
from .websocket_manager import ConnectionManager
from .tasks_models import Task, TaskTag, KanbanItem, TaskTagAssignment, TaskCustomList, ColumnsConfig, TaskHistory, KanbanSettings
from .tasks_schemas import (
    TaskCreate, TaskResponse, ListTasksResponse, DeleteResponse,
    BulkSyncRequest, BulkSyncResponse, BulkSyncItemResult,
    TaskTagCreate, TaskTagResponse, ListTagsResponse,
    TaskTagAssignmentCreate, TaskTagAssignmentResponse,
    TaskCustomListCreate, TaskCustomListResponse, ListCustomListsResponse,
    KanbanItemCreate, KanbanItemResponse, ListKanbanItemsResponse,
    KanbanSettingsCreate, KanbanSettingsResponse,
    ColumnsConfigCreate, ColumnsConfigResponse,
    ConflictErrorResponse, SyncStatsResponse
)

router = APIRouter(prefix="/api/tasks", tags=["Tasks & Kanban"])

# WebSocket manager instance
manager = ConnectionManager()

# Global ConnectionManager instance for WebSocket support
manager = ConnectionManager()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def db_task_to_response(db_task: Task) -> TaskResponse:
    """Convert DB Task to response schema"""
    return TaskResponse(
        id=db_task.id,
        user_id=db_task.user_id,
        parent_id=db_task.parent_id,
        title=db_task.title,
        description=db_task.description,
        status=db_task.status,
        due_date=db_task.due_date,
        completion_date=db_task.completion_date,
        alarm_date=db_task.alarm_date,
        note_id=db_task.note_id,
        custom_data=db_task.custom_data,
        archived=db_task.archived,
        order=db_task.order,
        created_at=db_task.created_at,
        updated_at=db_task.updated_at,
        deleted_at=db_task.deleted_at,
        synced_at=db_task.synced_at,
        version=db_task.version
    )


def db_tag_to_response(db_tag: TaskTag) -> TaskTagResponse:
    """Convert DB TaskTag to response schema"""
    return TaskTagResponse(
        id=db_tag.id,
        user_id=db_tag.user_id,
        name=db_tag.name,
        color=db_tag.color,
        created_at=db_tag.created_at,
        updated_at=db_tag.updated_at,
        deleted_at=db_tag.deleted_at,
        synced_at=db_tag.synced_at,
        version=db_tag.version
    )


def db_kanban_item_to_response(db_item: KanbanItem) -> KanbanItemResponse:
    """Convert DB KanbanItem to response schema"""
    return KanbanItemResponse(
        id=db_item.id,
        user_id=db_item.user_id,
        task_id=db_item.task_id,
        column_type=db_item.column_type,
        position=db_item.position,
        created_at=db_item.created_at,
        updated_at=db_item.updated_at,
        deleted_at=db_item.deleted_at,
        synced_at=db_item.synced_at,
        version=db_item.version
    )


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "tasks-sync",
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# TASK ENDPOINTS
# =============================================================================

@router.post("/task", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def upsert_task(
    request: TaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upsert (Create/Update) task with version-based conflict detection.
    Last-write-wins if incoming version >= stored version.
    """
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify other users' tasks"
            )
        
        existing_task = db.query(Task).filter(Task.id == request.id).first()
        
        if existing_task:
            # UPDATE - check version conflict
            if request.version < existing_task.version:
                # CONFLICT - return server data
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Version conflict detected",
                        "local_version": request.version,
                        "server_version": existing_task.version,
                        "server_data": db_task_to_response(existing_task).dict()
                    }
                )
            
            # Update fields
            existing_task.title = request.title
            existing_task.description = request.description
            existing_task.status = request.status
            existing_task.parent_id = request.parent_id
            existing_task.due_date = request.due_date
            existing_task.completion_date = request.completion_date
            existing_task.alarm_date = request.alarm_date
            existing_task.note_id = request.note_id
            existing_task.custom_data = request.custom_data
            existing_task.archived = request.archived
            existing_task.order = request.order
            existing_task.version = request.version + 1
            existing_task.synced_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_task)
            
            logger.info(f"Updated task: {existing_task.id} (v{existing_task.version})")
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'task')
            
            return db_task_to_response(existing_task)
        
        else:
            # CREATE new task
            new_task = Task(
                id=request.id,
                user_id=request.user_id,
                parent_id=request.parent_id,
                title=request.title,
                description=request.description,
                status=request.status,
                due_date=request.due_date,
                completion_date=request.completion_date,
                alarm_date=request.alarm_date,
                note_id=request.note_id,
                custom_data=request.custom_data,
                archived=request.archived,
                order=request.order,
                version=max(1, request.version),
                synced_at=datetime.utcnow()
            )
            
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            
            logger.info(f"Created task: {new_task.id}")
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'task')
            
            return db_task_to_response(new_task)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving task: {str(e)}"
        )


@router.get("/tasks", response_model=ListTasksResponse, status_code=status.HTTP_200_OK)
async def list_tasks(
    user_id: str = Query(..., description="User ID"),
    include_deleted: bool = Query(False, description="Include soft-deleted"),
    include_archived: bool = Query(True, description="Include archived"),
    parent_id: Optional[str] = Query(None, description="Filter by parent_id"),
    since: Optional[datetime] = Query(None, description="Get only modified after this date"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List user's tasks with filtering support for incremental sync"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users' tasks"
            )
        
        query = db.query(Task).filter(Task.user_id == user_id)
        
        if not include_deleted:
            query = query.filter(Task.deleted_at.is_(None))
        
        if not include_archived:
            query = query.filter(Task.archived == False)
        
        if parent_id is not None:
            query = query.filter(Task.parent_id == parent_id)
        
        if since:
            query = query.filter(Task.updated_at > since)
        
        query = query.order_by(Task.order.asc(), Task.created_at.desc())
        tasks = query.all()
        
        return ListTasksResponse(
            items=[db_task_to_response(task) for task in tasks],
            count=len(tasks),
            last_sync=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tasks: {str(e)}"
        )


@router.get("/task/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get single task by ID"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        if task.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        return db_task_to_response(task)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching task: {str(e)}"
        )


@router.delete("/task/{task_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: str,
    soft: bool = Query(True, description="Soft delete (deleted_at) or hard delete"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete task (soft delete by default, hard delete for testing)"""
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        if task.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete other user's task"
            )
        
        if soft:
            task.deleted_at = datetime.utcnow()
            task.version += 1
            db.commit()
            
            logger.info(f"Soft deleted task: {task_id}")
            
            # Notify WebSocket clients
            await emit_sync_required(task.user_id, 'task')
            
            return DeleteResponse(
                message="Task soft deleted",
                id=task_id,
                deleted_at=task.deleted_at
            )
        else:
            db.delete(task)
            db.commit()
            
            logger.warning(f"Hard deleted task: {task_id}")
            
            # Notify WebSocket clients
            await emit_sync_required(task.user_id, 'task')
            
            return DeleteResponse(
                message="Task permanently deleted",
                id=task_id,
                deleted_at=datetime.utcnow()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting task: {str(e)}"
        )


# =============================================================================
# TAG ENDPOINTS
# =============================================================================

@router.post("/tag", response_model=TaskTagResponse, status_code=status.HTTP_200_OK)
async def upsert_tag(
    request: TaskTagCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upsert (Create/Update) task tag"""
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify other users' tags"
            )
        
        existing_tag = db.query(TaskTag).filter(TaskTag.id == request.id).first()
        
        if existing_tag:
            if request.version < existing_tag.version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Version conflict in tag",
                        "local_version": request.version,
                        "server_version": existing_tag.version,
                        "server_data": db_tag_to_response(existing_tag).dict()
                    }
                )
            
            existing_tag.name = request.name
            existing_tag.color = request.color
            existing_tag.version = request.version + 1
            existing_tag.synced_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_tag)
            
            logger.info(f"Updated tag: {existing_tag.id}")
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'tag')
            
            return db_tag_to_response(existing_tag)
        
        else:
            new_tag = TaskTag(
                id=request.id,
                user_id=request.user_id,
                name=request.name,
                color=request.color,
                version=max(1, request.version),
                synced_at=datetime.utcnow()
            )
            
            db.add(new_tag)
            db.commit()
            db.refresh(new_tag)
            
            logger.info(f"Created tag: {new_tag.id}")
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'tag')
            
            return db_tag_to_response(new_tag)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting tag: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving tag: {str(e)}"
        )


@router.get("/tags", response_model=ListTagsResponse, status_code=status.HTTP_200_OK)
async def list_tags(
    user_id: str = Query(..., description="User ID"),
    include_deleted: bool = Query(False, description="Include deleted"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List user's tags"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view other users' tags"
            )
        
        query = db.query(TaskTag).filter(TaskTag.user_id == user_id)
        
        if not include_deleted:
            query = query.filter(TaskTag.deleted_at.is_(None))
        
        query = query.order_by(TaskTag.name.asc())
        tags = query.all()
        
        return ListTagsResponse(
            items=[db_tag_to_response(tag) for tag in tags],
            count=len(tags)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tags: {str(e)}"
        )


@router.delete("/tag/{tag_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_tag(
    tag_id: str,
    soft: bool = Query(True, description="Soft delete"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete tag"""
    try:
        tag = db.query(TaskTag).filter(TaskTag.id == tag_id).first()
        
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag {tag_id} not found"
            )
        
        if tag.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if soft:
            tag.deleted_at = datetime.utcnow()
            tag.version += 1
            db.commit()
            
            # Notify WebSocket clients
            await emit_sync_required(tag.user_id, 'tag')
            
            return DeleteResponse(
                message="Tag soft deleted",
                id=tag_id,
                deleted_at=tag.deleted_at
            )
        else:
            db.delete(tag)
            db.commit()
            
            # Notify WebSocket clients
            await emit_sync_required(tag.user_id, 'tag')
            
            return DeleteResponse(
                message="Tag permanently deleted",
                id=tag_id,
                deleted_at=datetime.utcnow()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting tag {tag_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting tag: {str(e)}"
        )


# =============================================================================
# KANBAN ENDPOINTS
# =============================================================================

@router.post("/kanban/item", response_model=KanbanItemResponse, status_code=status.HTTP_200_OK)
async def upsert_kanban_item(
    request: KanbanItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upsert Kanban item (task position in column)"""
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        existing_item = db.query(KanbanItem).filter(KanbanItem.id == request.id).first()
        
        if existing_item:
            if request.version < existing_item.version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Version conflict in Kanban item",
                        "local_version": request.version,
                        "server_version": existing_item.version,
                        "server_data": db_kanban_item_to_response(existing_item).dict()
                    }
                )
            
            existing_item.task_id = request.task_id
            existing_item.column_type = request.column_type
            existing_item.position = request.position
            existing_item.version = request.version + 1
            existing_item.synced_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_item)
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'kanban_item')
            
            return db_kanban_item_to_response(existing_item)
        
        else:
            new_item = KanbanItem(
                id=request.id,
                user_id=request.user_id,
                task_id=request.task_id,
                column_type=request.column_type,
                position=request.position,
                version=max(1, request.version),
                synced_at=datetime.utcnow()
            )
            
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'kanban_item')
            
            return db_kanban_item_to_response(new_item)
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting kanban item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving Kanban item: {str(e)}"
        )


@router.get("/kanban/items", response_model=ListKanbanItemsResponse, status_code=status.HTTP_200_OK)
async def list_kanban_items(
    user_id: str = Query(..., description="User ID"),
    column_type: Optional[str] = Query(None, description="Filter by column"),
    include_deleted: bool = Query(False, description="Include deleted"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List Kanban items"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        query = db.query(KanbanItem).filter(KanbanItem.user_id == user_id)
        
        if not include_deleted:
            query = query.filter(KanbanItem.deleted_at.is_(None))
        
        if column_type:
            query = query.filter(KanbanItem.column_type == column_type)
        
        query = query.order_by(KanbanItem.column_type.asc(), KanbanItem.position.asc())
        items = query.all()
        
        return ListKanbanItemsResponse(
            items=[db_kanban_item_to_response(item) for item in items],
            count=len(items)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing kanban items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Kanban items: {str(e)}"
        )


# =============================================================================
# BULK SYNC ENDPOINT
# =============================================================================

@router.post("/bulk-sync", response_model=BulkSyncResponse, status_code=status.HTTP_200_OK)
async def bulk_sync(
    request: BulkSyncRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk synchronization - sync multiple items in one request.
    
    Supports:
    - Tasks (max 100)
    - Tags (max 100)
    - Tag assignments
    - Kanban items
    - Custom lists
    
    Returns results for each item (success/conflict/error).
    """
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        results = []
        success_count = 0
        conflict_count = 0
        error_count = 0
        
        # Sync tasks
        for task_data in request.tasks:
            try:
                existing = db.query(Task).filter(Task.id == task_data.id).first()
                
                if existing and task_data.version < existing.version:
                    # Conflict
                    results.append(BulkSyncItemResult(
                        id=task_data.id,
                        entity_type='task',
                        status='conflict',
                        server_version=existing.version
                    ))
                    conflict_count += 1
                elif existing:
                    # Update
                    existing.title = task_data.title
                    existing.description = task_data.description
                    existing.status = task_data.status
                    existing.parent_id = task_data.parent_id
                    existing.due_date = task_data.due_date
                    existing.completion_date = task_data.completion_date
                    existing.alarm_date = task_data.alarm_date
                    existing.note_id = task_data.note_id
                    existing.custom_data = task_data.custom_data
                    existing.archived = task_data.archived
                    existing.order = task_data.order
                    existing.version = task_data.version + 1
                    existing.synced_at = datetime.utcnow()
                    
                    results.append(BulkSyncItemResult(
                        id=task_data.id,
                        entity_type='task',
                        status='success',
                        version=existing.version
                    ))
                    success_count += 1
                else:
                    # Create
                    new_task = Task(
                        id=task_data.id,
                        user_id=request.user_id,
                        parent_id=task_data.parent_id,
                        title=task_data.title,
                        description=task_data.description,
                        status=task_data.status,
                        due_date=task_data.due_date,
                        completion_date=task_data.completion_date,
                        alarm_date=task_data.alarm_date,
                        note_id=task_data.note_id,
                        custom_data=task_data.custom_data,
                        archived=task_data.archived,
                        order=task_data.order,
                        version=max(1, task_data.version),
                        synced_at=datetime.utcnow()
                    )
                    db.add(new_task)
                    
                    results.append(BulkSyncItemResult(
                        id=task_data.id,
                        entity_type='task',
                        status='success',
                        version=1
                    ))
                    success_count += 1
            
            except Exception as e:
                results.append(BulkSyncItemResult(
                    id=task_data.id,
                    entity_type='task',
                    status='error',
                    error=str(e)
                ))
                error_count += 1
        
        # Sync tags
        for tag_data in request.tags:
            try:
                existing = db.query(TaskTag).filter(TaskTag.id == tag_data.id).first()
                
                if existing and tag_data.version < existing.version:
                    results.append(BulkSyncItemResult(
                        id=tag_data.id,
                        entity_type='tag',
                        status='conflict',
                        server_version=existing.version
                    ))
                    conflict_count += 1
                elif existing:
                    existing.name = tag_data.name
                    existing.color = tag_data.color
                    existing.version = tag_data.version + 1
                    existing.synced_at = datetime.utcnow()
                    
                    results.append(BulkSyncItemResult(
                        id=tag_data.id,
                        entity_type='tag',
                        status='success',
                        version=existing.version
                    ))
                    success_count += 1
                else:
                    new_tag = TaskTag(
                        id=tag_data.id,
                        user_id=request.user_id,
                        name=tag_data.name,
                        color=tag_data.color,
                        version=max(1, tag_data.version),
                        synced_at=datetime.utcnow()
                    )
                    db.add(new_tag)
                    
                    results.append(BulkSyncItemResult(
                        id=tag_data.id,
                        entity_type='tag',
                        status='success',
                        version=1
                    ))
                    success_count += 1
            
            except Exception as e:
                results.append(BulkSyncItemResult(
                    id=tag_data.id,
                    entity_type='tag',
                    status='error',
                    error=str(e)
                ))
                error_count += 1
        
        # Sync Kanban items
        for kanban_data in request.kanban_items:
            try:
                existing = db.query(KanbanItem).filter(KanbanItem.id == kanban_data.id).first()
                
                if existing and kanban_data.version < existing.version:
                    results.append(BulkSyncItemResult(
                        id=kanban_data.id,
                        entity_type='kanban_item',
                        status='conflict',
                        server_version=existing.version
                    ))
                    conflict_count += 1
                elif existing:
                    existing.task_id = kanban_data.task_id
                    existing.column_type = kanban_data.column_type
                    existing.position = kanban_data.position
                    existing.version = kanban_data.version + 1
                    existing.synced_at = datetime.utcnow()
                    
                    results.append(BulkSyncItemResult(
                        id=kanban_data.id,
                        entity_type='kanban_item',
                        status='success',
                        version=existing.version
                    ))
                    success_count += 1
                else:
                    new_item = KanbanItem(
                        id=kanban_data.id,
                        user_id=request.user_id,
                        task_id=kanban_data.task_id,
                        column_type=kanban_data.column_type,
                        position=kanban_data.position,
                        version=max(1, kanban_data.version),
                        synced_at=datetime.utcnow()
                    )
                    db.add(new_item)
                    
                    results.append(BulkSyncItemResult(
                        id=kanban_data.id,
                        entity_type='kanban_item',
                        status='success',
                        version=1
                    ))
                    success_count += 1
            
            except Exception as e:
                results.append(BulkSyncItemResult(
                    id=kanban_data.id,
                    entity_type='kanban_item',
                    status='error',
                    error=str(e)
                ))
                error_count += 1
        
        # Commit all changes
        db.commit()
        
        # Notify WebSocket clients about changes
        if request.tasks:
            await emit_sync_required(request.user_id, 'task')
        if request.tags:
            await emit_sync_required(request.user_id, 'tag')
        if request.kanban_items:
            await emit_sync_required(request.user_id, 'kanban_item')
        
        logger.info(f"Bulk sync completed: {success_count} success, {conflict_count} conflicts, {error_count} errors")
        
        return BulkSyncResponse(
            results=results,
            success_count=success_count,
            conflict_count=conflict_count,
            error_count=error_count,
            server_timestamp=datetime.utcnow()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in bulk sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during bulk sync: {str(e)}"
        )


# =============================================================================
# CUSTOM LISTS ENDPOINTS
# =============================================================================

@router.post("/custom-list", response_model=TaskCustomListResponse, status_code=status.HTTP_200_OK)
async def upsert_custom_list(
    request: TaskCustomListCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upsert (Create/Update) custom list"""
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        existing = db.query(TaskCustomList).filter(TaskCustomList.id == request.id).first()
        
        if existing:
            if request.version < existing.version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Version conflict in custom list",
                        "local_version": request.version,
                        "server_version": existing.version
                    }
                )
            
            existing.name = request.name
            existing.values = request.values
            existing.version = request.version + 1
            existing.synced_at = datetime.utcnow()
            
            db.commit()
            db.refresh(existing)
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'custom_list')
            
            return TaskCustomListResponse(
                id=existing.id,
                user_id=existing.user_id,
                name=existing.name,
                values=existing.values,
                version=existing.version,
                created_at=existing.created_at,
                updated_at=existing.updated_at,
                deleted_at=existing.deleted_at,
                synced_at=existing.synced_at
            )
        
        else:
            new_list = TaskCustomList(
                id=request.id,
                user_id=request.user_id,
                name=request.name,
                values=request.values,
                version=max(1, request.version),
                synced_at=datetime.utcnow()
            )
            
            db.add(new_list)
            db.commit()
            db.refresh(new_list)
            
            # Notify WebSocket clients
            await emit_sync_required(request.user_id, 'custom_list')
            
            return TaskCustomListResponse(
                id=new_list.id,
                user_id=new_list.user_id,
                name=new_list.name,
                values=new_list.values,
                version=new_list.version,
                created_at=new_list.created_at,
                updated_at=new_list.updated_at,
                deleted_at=new_list.deleted_at,
                synced_at=new_list.synced_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting custom list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving custom list: {str(e)}"
        )


@router.get("/custom-lists", response_model=ListCustomListsResponse, status_code=status.HTTP_200_OK)
async def list_custom_lists(
    user_id: str = Query(..., description="User ID"),
    include_deleted: bool = Query(False, description="Include deleted"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List user's custom lists"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        query = db.query(TaskCustomList).filter(TaskCustomList.user_id == user_id)
        
        if not include_deleted:
            query = query.filter(TaskCustomList.deleted_at.is_(None))
        
        query = query.order_by(TaskCustomList.name.asc())
        lists = query.all()
        
        return ListCustomListsResponse(
            items=[
                TaskCustomListResponse(
                    id=l.id,
                    user_id=l.user_id,
                    name=l.name,
                    values=l.values,
                    version=l.version,
                    created_at=l.created_at,
                    updated_at=l.updated_at,
                    deleted_at=l.deleted_at,
                    synced_at=l.synced_at
                )
                for l in lists
            ],
            count=len(lists)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing custom lists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching custom lists: {str(e)}"
        )


@router.delete("/custom-list/{list_id}", response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_custom_list(
    list_id: str,
    soft: bool = Query(True, description="Soft delete"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete custom list"""
    try:
        custom_list = db.query(TaskCustomList).filter(TaskCustomList.id == list_id).first()
        
        if not custom_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom list {list_id} not found"
            )
        
        if custom_list.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        if soft:
            custom_list.deleted_at = datetime.utcnow()
            custom_list.version += 1
            db.commit()
            
            # Notify WebSocket clients
            await emit_sync_required(custom_list.user_id, 'custom_list')
            
            return DeleteResponse(
                message="Custom list soft deleted",
                id=list_id,
                deleted_at=custom_list.deleted_at
            )
        else:
            db.delete(custom_list)
            db.commit()
            
            # Notify WebSocket clients
            await emit_sync_required(custom_list.user_id, 'custom_list')
            
            return DeleteResponse(
                message="Custom list permanently deleted",
                id=list_id,
                deleted_at=datetime.utcnow()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting custom list {list_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting custom list: {str(e)}"
        )


# =============================================================================
# KANBAN SETTINGS & COLUMNS CONFIG ENDPOINTS
# =============================================================================

@router.get("/kanban/settings", response_model=KanbanSettingsResponse, status_code=status.HTTP_200_OK)
async def get_kanban_settings(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user's Kanban settings"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        settings = db.query(KanbanSettings).filter(
            KanbanSettings.user_id == user_id
        ).first()
        
        if not settings:
            # Return default empty settings
            return KanbanSettingsResponse(
                id="default",
                user_id=user_id,
                settings={},
                version=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        
        return KanbanSettingsResponse(
            id=settings.id,
            user_id=settings.user_id,
            settings=settings.settings,
            version=settings.version,
            created_at=settings.created_at,
            updated_at=settings.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting kanban settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching settings: {str(e)}"
        )


@router.post("/kanban/settings", response_model=KanbanSettingsResponse, status_code=status.HTTP_200_OK)
async def upsert_kanban_settings(
    request: KanbanSettingsCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upsert Kanban settings"""
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        existing = db.query(KanbanSettings).filter(
            KanbanSettings.id == request.id
        ).first()
        
        if existing:
            if request.version < existing.version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Version conflict in settings",
                        "local_version": request.version,
                        "server_version": existing.version
                    }
                )
            
            existing.settings = request.settings
            existing.version = request.version + 1
            
            db.commit()
            db.refresh(existing)
            
            return KanbanSettingsResponse(
                id=existing.id,
                user_id=existing.user_id,
                settings=existing.settings,
                version=existing.version,
                created_at=existing.created_at,
                updated_at=existing.updated_at
            )
        
        else:
            new_settings = KanbanSettings(
                id=request.id,
                user_id=request.user_id,
                settings=request.settings,
                version=max(1, request.version)
            )
            
            db.add(new_settings)
            db.commit()
            db.refresh(new_settings)
            
            return KanbanSettingsResponse(
                id=new_settings.id,
                user_id=new_settings.user_id,
                settings=new_settings.settings,
                version=new_settings.version,
                created_at=new_settings.created_at,
                updated_at=new_settings.updated_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting kanban settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving settings: {str(e)}"
        )


@router.get("/columns-config", response_model=ColumnsConfigResponse, status_code=status.HTTP_200_OK)
async def get_columns_config(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user's columns configuration (visible columns, order, sort)"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        config = db.query(ColumnsConfig).filter(
            ColumnsConfig.user_id == user_id
        ).first()
        
        if not config:
            # Return default config
            return ColumnsConfigResponse(
                id="default",
                user_id=user_id,
                visible_columns=[],
                column_order=[],
                sort_column=None,
                sort_direction="asc",
                version=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        
        return ColumnsConfigResponse(
            id=config.id,
            user_id=config.user_id,
            visible_columns=config.visible_columns,
            column_order=config.column_order,
            sort_column=config.sort_column,
            sort_direction=config.sort_direction,
            version=config.version,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting columns config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching config: {str(e)}"
        )


@router.post("/columns-config", response_model=ColumnsConfigResponse, status_code=status.HTTP_200_OK)
async def upsert_columns_config(
    request: ColumnsConfigCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upsert columns configuration"""
    try:
        if request.user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        existing = db.query(ColumnsConfig).filter(
            ColumnsConfig.id == request.id
        ).first()
        
        if existing:
            if request.version < existing.version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Version conflict in columns config",
                        "local_version": request.version,
                        "server_version": existing.version
                    }
                )
            
            existing.visible_columns = request.visible_columns
            existing.column_order = request.column_order
            existing.sort_column = request.sort_column
            existing.sort_direction = request.sort_direction
            existing.version = request.version + 1
            
            db.commit()
            db.refresh(existing)
            
            return ColumnsConfigResponse(
                id=existing.id,
                user_id=existing.user_id,
                visible_columns=existing.visible_columns,
                column_order=existing.column_order,
                sort_column=existing.sort_column,
                sort_direction=existing.sort_direction,
                version=existing.version,
                created_at=existing.created_at,
                updated_at=existing.updated_at
            )
        
        else:
            new_config = ColumnsConfig(
                id=request.id,
                user_id=request.user_id,
                visible_columns=request.visible_columns,
                column_order=request.column_order,
                sort_column=request.sort_column,
                sort_direction=request.sort_direction,
                version=max(1, request.version)
            )
            
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            
            return ColumnsConfigResponse(
                id=new_config.id,
                user_id=new_config.user_id,
                visible_columns=new_config.visible_columns,
                column_order=new_config.column_order,
                sort_column=new_config.sort_column,
                sort_direction=new_config.sort_direction,
                version=new_config.version,
                created_at=new_config.created_at,
                updated_at=new_config.updated_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting columns config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving config: {str(e)}"
        )


# =============================================================================
# STATS ENDPOINT
# =============================================================================

@router.get("/stats", response_model=SyncStatsResponse, status_code=status.HTTP_200_OK)
async def get_sync_stats(
    user_id: str = Query(..., description="User ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get user's synchronization statistics"""
    try:
        if user_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Last sync
        last_sync_task = db.query(func.max(Task.synced_at)).filter(
            Task.user_id == user_id
        ).scalar()
        
        # Pending (not synced)
        pending_tasks = db.query(func.count(Task.id)).filter(
            and_(
                Task.user_id == user_id,
                Task.synced_at.is_(None),
                Task.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        pending_tags = db.query(func.count(TaskTag.id)).filter(
            and_(
                TaskTag.user_id == user_id,
                TaskTag.synced_at.is_(None),
                TaskTag.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        pending_kanban = db.query(func.count(KanbanItem.id)).filter(
            and_(
                KanbanItem.user_id == user_id,
                KanbanItem.synced_at.is_(None),
                KanbanItem.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        # Total counts
        total_tasks = db.query(func.count(Task.id)).filter(
            and_(
                Task.user_id == user_id,
                Task.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        total_tags = db.query(func.count(TaskTag.id)).filter(
            and_(
                TaskTag.user_id == user_id,
                TaskTag.deleted_at.is_(None)
            )
        ).scalar() or 0
        
        return SyncStatsResponse(
            user_id=user_id,
            last_sync=last_sync_task,
            pending_tasks=pending_tasks,
            pending_tags=pending_tags,
            pending_kanban_items=pending_kanban,
            total_tasks=total_tasks,
            total_tags=total_tags
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sync stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time task synchronization.
    
    Clients connect with JWT token and receive SYNC_REQUIRED events
    when tasks/tags/kanban items are modified by other devices.
    
    Usage:
    ws://server/api/tasks/ws?token=<jwt_token>
    
    Events sent to client:
    - {"type": "SYNC_REQUIRED", "entity_type": "task", "timestamp": "..."}
    - {"type": "ITEM_CHANGED", "entity_type": "task", "item_id": "...", ...}
    - {"type": "PING"}
    
    Client should respond to PING with {"type": "PONG"}.
    """
    user_id = None
    
    try:
        # Decode token to get user_id
        payload = decode_token(token)
        user_id = payload.get("user_id") or payload.get("sub")  # sub is the user_id in JWT
        
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token: missing user_id")
            return
        
        # Accept connection and register
        await manager.connect(websocket, user_id)
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "CONNECTED",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Tasks WebSocket connected"
        }, websocket)
        
        # Keep connection alive and handle incoming messages
        try:
            while True:
                # Wait for messages from client (e.g., PONG responses)
                data = await websocket.receive_json()
                
                # Handle PONG
                if data.get('type') == 'PONG':
                    logger.debug(f"Received PONG from user {user_id}")
                    continue
                
                # Handle other client messages if needed
                logger.debug(f"Received message from user {user_id}: {data}")
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
    
    finally:
        # Cleanup
        if user_id:
            await manager.disconnect(websocket, user_id)


# =============================================================================
# HELPER: Emit sync events to WebSocket clients
# =============================================================================

async def emit_sync_required(user_id: str, entity_type: str):
    """
    Emit SYNC_REQUIRED event to all user's WebSocket connections.
    
    Call this after creating/updating/deleting tasks, tags, kanban items etc.
    to notify other connected devices to pull fresh data.
    """
    await manager.broadcast_to_user({
        "type": "SYNC_REQUIRED",
        "entity_type": entity_type,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)


async def emit_item_changed(user_id: str, entity_type: str, item_id: str, action: str):
    """
    Emit ITEM_CHANGED event with specific item details.
    
    action: "created", "updated", "deleted"
    """
    await manager.broadcast_to_user({
        "type": "ITEM_CHANGED",
        "entity_type": entity_type,
        "item_id": item_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }, user_id)
