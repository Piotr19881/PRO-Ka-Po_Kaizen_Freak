"""
Tasks Models - Modele danych dla synchronizacji z API
Kompatybilne z Render_upload/app/tasks_schemas.py
"""
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from enum import Enum


class TaskStatus(Enum):
    """Status zadania"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Model zadania - kompatybilny z API"""
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: str = "todo"
    parent_id: Optional[str] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    alarm_date: Optional[datetime] = None
    note_id: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None
    archived: bool = False
    order: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik dla API"""
        # Konwersja status string → boolean dla API
        # Backend używa: False=todo, True=done
        status_bool = False
        if isinstance(self.status, str):
            status_bool = self.status.lower() in ('done', 'completed', 'finished', 'true', '1')
        elif isinstance(self.status, bool):
            status_bool = self.status
        else:
            status_bool = bool(self.status)
        
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'status': status_bool,  # Boolean: False=todo, True=done
            'parent_id': self.parent_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'alarm_date': self.alarm_date.isoformat() if self.alarm_date else None,
            'note_id': self.note_id,
            'custom_data': self.custom_data or {},
            'archived': self.archived,
            'order': self.order,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
        return data
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        """Utwórz z słownika (z API lub bazy)"""
        # Konwersja status boolean → string dla lokalnej bazy
        # Backend używa: False=todo, True=done
        status_value = data.get('status', 'todo')
        if isinstance(status_value, bool):
            status_str = 'done' if status_value else 'todo'
        else:
            status_str = str(status_value) if status_value else 'todo'
        
        return Task(
            id=data['id'],
            user_id=data['user_id'],
            title=data['title'],
            description=data.get('description'),
            status=status_str,
            parent_id=data.get('parent_id'),
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            completion_date=datetime.fromisoformat(data['completion_date']) if data.get('completion_date') else None,
            alarm_date=datetime.fromisoformat(data['alarm_date']) if data.get('alarm_date') else None,
            note_id=data.get('note_id'),
            custom_data=data.get('custom_data'),
            archived=data.get('archived', False),
            order=data.get('order', 0),
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            deleted_at=datetime.fromisoformat(data['deleted_at']) if data.get('deleted_at') else None,
            synced_at=datetime.fromisoformat(data['synced_at']) if data.get('synced_at') else None
        )
    
    @staticmethod
    def from_local_db(data: Dict[str, Any], server_id: Optional[str] = None) -> 'Task':
        """
        Konwertuj z lokalnej bazy danych (która używa innych nazw kolumn)
        do modelu Task kompatybilnego z API
        
        Args:
            data: Słownik z lokalnej bazy (id=INTEGER, status=BOOLEAN itp.)
            server_id: Opcjonalnie mapowanie local id → server UUID
        """
        # Mapowanie lokalnego 'id' (INTEGER) na UUID dla API
        task_id = server_id or str(data.get('id', ''))
        
        # Lokalna baza ma 'status' jako BOOLEAN, API używa enum string
        local_status = data.get('status', False)
        api_status = 'done' if local_status else 'todo'
        
        # Custom data może być string JSON w bazie
        custom_data = data.get('custom_data')
        if isinstance(custom_data, str):
            import json
            try:
                custom_data = json.loads(custom_data)
            except:
                custom_data = {}
        
        return Task(
            id=task_id,
            user_id=str(data.get('user_id', '')),
            title=data.get('title', 'Untitled'),
            description=data.get('description'),
            status=api_status,
            parent_id=str(data['parent_id']) if data.get('parent_id') else None,
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            completion_date=datetime.fromisoformat(data['completion_date']) if data.get('completion_date') else None,
            alarm_date=datetime.fromisoformat(data['alarm_date']) if data.get('alarm_date') else None,
            note_id=str(data['note_id']) if data.get('note_id') else None,
            custom_data=custom_data or {},
            archived=data.get('archived', False),
            order=data.get('position', 0),  # local DB uses 'position'
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            deleted_at=datetime.fromisoformat(data['deleted_at']) if data.get('deleted_at') else None,
            synced_at=datetime.fromisoformat(data['synced_at']) if data.get('synced_at') else None
        )


@dataclass
class TaskTag:
    """Model tagu zadania"""
    id: str
    user_id: str
    name: str
    color: str = "#CCCCCC"
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik dla API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskTag':
        """Utwórz z słownika"""
        return TaskTag(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            color=data.get('color', '#CCCCCC'),
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            deleted_at=datetime.fromisoformat(data['deleted_at']) if data.get('deleted_at') else None,
            synced_at=datetime.fromisoformat(data['synced_at']) if data.get('synced_at') else None
        )


@dataclass
class KanbanItem:
    """Model elementu Kanban - pozycja zadania w kolumnie"""
    id: str
    user_id: str
    task_id: str
    column_type: str
    position: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik dla API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'task_id': self.task_id,
            'column_type': self.column_type,
            'position': self.position,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'KanbanItem':
        """Utwórz z słownika"""
        return KanbanItem(
            id=data['id'],
            user_id=data['user_id'],
            task_id=data['task_id'],
            column_type=data['column_type'],
            position=data.get('position', 0),
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            deleted_at=datetime.fromisoformat(data['deleted_at']) if data.get('deleted_at') else None,
            synced_at=datetime.fromisoformat(data['synced_at']) if data.get('synced_at') else None
        )


@dataclass
class TaskCustomList:
    """Model listy własnej użytkownika (wartości dla konfigurow alnych kolumn)"""
    id: str
    user_id: str
    name: str
    values: List[str] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik dla API"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'values': self.values,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskCustomList':
        """Utwórz z słownika"""
        return TaskCustomList(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            values=data.get('values', []),
            version=data.get('version', 1),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            deleted_at=datetime.fromisoformat(data['deleted_at']) if data.get('deleted_at') else None,
            synced_at=datetime.fromisoformat(data['synced_at']) if data.get('synced_at') else None
        )


@dataclass
class TaskTagAssignment:
    """Przypisanie tagu do zadania"""
    id: str
    task_id: str
    tag_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'tag_id': self.tag_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskTagAssignment':
        """Utwórz z słownika"""
        return TaskTagAssignment(
            id=data['id'],
            task_id=data['task_id'],
            tag_id=data['tag_id'],
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.utcnow()
        )
