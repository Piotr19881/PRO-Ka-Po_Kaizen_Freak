"""
Tasks Models - Modele danych dla zadań, tagów i Kanban
Local-first architecture z synchronizacją do backend API
"""
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class TaskStatus(Enum):
    """Status zadania"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class KanbanColumnType(Enum):
    """Typy kolumn Kanban"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BACKLOG = "backlog"
    CUSTOM = "custom"


@dataclass
class Task:
    """
    Model zadania.
    
    Local-first: przechowywane lokalnie w SQLite z metadanymi sync (version, synced_at, deleted_at)
    """
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    parent_id: Optional[str] = None  # Dla subtasków
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    alarm_date: Optional[datetime] = None
    note_id: Optional[str] = None  # Link do notatki
    custom_data: Dict[str, Any] = field(default_factory=dict)  # Dodatkowe pola (currency, duration, etc.)
    archived: bool = False
    order: int = 0  # Pozycja w liście
    
    # Synchronization metadata
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik dla API/Database"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value if isinstance(self.status, TaskStatus) else self.status,
            'parent_id': self.parent_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'alarm_date': self.alarm_date.isoformat() if self.alarm_date else None,
            'note_id': self.note_id,
            'custom_data': json.dumps(self.custom_data) if isinstance(self.custom_data, dict) else self.custom_data,
            'archived': self.archived,
            'order': self.order,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        """Utwórz z słownika (z API lub Database)"""
        # Parse datetime fields
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # Parse custom_data (może być string JSON lub dict)
        custom_data = data.get('custom_data', {})
        if isinstance(custom_data, str):
            try:
                custom_data = json.loads(custom_data) if custom_data else {}
            except json.JSONDecodeError:
                custom_data = {}
        
        # Parse status
        status = data.get('status', 'todo')
        if isinstance(status, str):
            status = TaskStatus(status)
        
        return Task(
            id=data['id'],
            user_id=data['user_id'],
            title=data['title'],
            description=data.get('description'),
            status=status,
            parent_id=data.get('parent_id'),
            due_date=parse_datetime(data.get('due_date')),
            completion_date=parse_datetime(data.get('completion_date')),
            alarm_date=parse_datetime(data.get('alarm_date')),
            note_id=data.get('note_id'),
            custom_data=custom_data,
            archived=data.get('archived', False),
            order=data.get('order', 0),
            version=data.get('version', 1),
            created_at=parse_datetime(data.get('created_at')) or datetime.utcnow(),
            updated_at=parse_datetime(data.get('updated_at')),
            deleted_at=parse_datetime(data.get('deleted_at')),
            synced_at=parse_datetime(data.get('synced_at')),
        )


@dataclass
class TaskTag:
    """
    Model tagu zadania.
    
    Tagi służą do kategoryzacji zadań (np. "Praca", "Dom", "Pilne")
    """
    id: str
    user_id: str
    name: str
    color: str = "#3498db"  # Domyślny kolor (niebieski)
    
    # Synchronization metadata
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskTag':
        """Utwórz z słownika"""
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        return TaskTag(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            color=data.get('color', '#3498db'),
            version=data.get('version', 1),
            created_at=parse_datetime(data.get('created_at')) or datetime.utcnow(),
            updated_at=parse_datetime(data.get('updated_at')),
            deleted_at=parse_datetime(data.get('deleted_at')),
            synced_at=parse_datetime(data.get('synced_at')),
        )


@dataclass
class TaskTagAssignment:
    """
    Przypisanie tagu do zadania (relacja many-to-many).
    """
    id: str
    task_id: str
    tag_id: str
    user_id: str
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'tag_id': self.tag_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskTagAssignment':
        """Utwórz z słownika"""
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not created_at:
            created_at = datetime.utcnow()
        
        return TaskTagAssignment(
            id=data['id'],
            task_id=data['task_id'],
            tag_id=data['tag_id'],
            user_id=data['user_id'],
            created_at=created_at,
        )


@dataclass
class KanbanItem:
    """
    Pozycja zadania na tablicy Kanban.
    
    Przechowuje informacje o pozycji zadania w kolumnie (column_type, position)
    """
    id: str
    user_id: str
    task_id: str
    column_type: str  # "todo", "in_progress", "done", etc.
    position: int = 0  # Pozycja w kolumnie (dla drag & drop)
    
    # Synchronization metadata
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
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
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'KanbanItem':
        """Utwórz z słownika"""
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        return KanbanItem(
            id=data['id'],
            user_id=data['user_id'],
            task_id=data['task_id'],
            column_type=data['column_type'],
            position=data.get('position', 0),
            version=data.get('version', 1),
            created_at=parse_datetime(data.get('created_at')) or datetime.utcnow(),
            updated_at=parse_datetime(data.get('updated_at')),
            deleted_at=parse_datetime(data.get('deleted_at')),
            synced_at=parse_datetime(data.get('synced_at')),
        )


@dataclass
class TaskCustomList:
    """
    Niestandardowa lista wartości dla custom fields.
    
    Pozwala użytkownikowi definiować własne listy wyboru (np. lista projektów, klientów)
    """
    id: str
    user_id: str
    name: str  # Nazwa listy (np. "Projekty", "Klienci")
    values: List[str] = field(default_factory=list)  # Lista wartości
    
    # Synchronization metadata
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'values': json.dumps(self.values) if isinstance(self.values, list) else self.values,
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TaskCustomList':
        """Utwórz z słownika"""
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # Parse values (może być string JSON lub lista)
        values = data.get('values', [])
        if isinstance(values, str):
            try:
                values = json.loads(values) if values else []
            except json.JSONDecodeError:
                values = []
        
        return TaskCustomList(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            values=values,
            version=data.get('version', 1),
            created_at=parse_datetime(data.get('created_at')) or datetime.utcnow(),
            updated_at=parse_datetime(data.get('updated_at')),
            deleted_at=parse_datetime(data.get('deleted_at')),
            synced_at=parse_datetime(data.get('synced_at')),
        )


@dataclass
class KanbanSettings:
    """
    Ustawienia tablicy Kanban użytkownika.
    
    Przechowuje konfigurację kolumn i inne ustawienia wyświetlania
    """
    id: str
    user_id: str
    settings: Dict[str, Any] = field(default_factory=dict)  # JSON blob z ustawieniami
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'settings': json.dumps(self.settings) if isinstance(self.settings, dict) else self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'KanbanSettings':
        """Utwórz z słownika"""
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # Parse settings
        settings = data.get('settings', {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings) if settings else {}
            except json.JSONDecodeError:
                settings = {}
        
        return KanbanSettings(
            id=data['id'],
            user_id=data['user_id'],
            settings=settings,
            created_at=parse_datetime(data.get('created_at')) or datetime.utcnow(),
            updated_at=parse_datetime(data.get('updated_at')),
        )


@dataclass
class ColumnsConfig:
    """
    Konfiguracja kolumn dla widoku zadań.
    
    Przechowuje preferencje użytkownika dotyczące widoczności i kolejności kolumn
    """
    id: str
    user_id: str
    visible_columns: List[str] = field(default_factory=list)  # Lista widocznych kolumn
    column_order: List[str] = field(default_factory=list)  # Kolejność kolumn
    sort_config: Dict[str, Any] = field(default_factory=dict)  # Konfiguracja sortowania
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'visible_columns': json.dumps(self.visible_columns) if isinstance(self.visible_columns, list) else self.visible_columns,
            'column_order': json.dumps(self.column_order) if isinstance(self.column_order, list) else self.column_order,
            'sort_config': json.dumps(self.sort_config) if isinstance(self.sort_config, dict) else self.sort_config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ColumnsConfig':
        """Utwórz z słownika"""
        def parse_datetime(dt_str):
            if not dt_str:
                return None
            if isinstance(dt_str, datetime):
                return dt_str
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # Parse JSON fields
        def parse_json_field(field_data, default):
            if isinstance(field_data, str):
                try:
                    return json.loads(field_data) if field_data else default
                except json.JSONDecodeError:
                    return default
            return field_data if field_data is not None else default
        
        return ColumnsConfig(
            id=data['id'],
            user_id=data['user_id'],
            visible_columns=parse_json_field(data.get('visible_columns'), []),
            column_order=parse_json_field(data.get('column_order'), []),
            sort_config=parse_json_field(data.get('sort_config'), {}),
            created_at=parse_datetime(data.get('created_at')) or datetime.utcnow(),
            updated_at=parse_datetime(data.get('updated_at')),
        )
