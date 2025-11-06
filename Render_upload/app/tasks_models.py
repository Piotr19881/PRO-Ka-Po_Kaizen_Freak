"""
SQLAlchemy Models dla Tasks & Kanban
Schema: s06_tasks
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime

from .database import Base


# =============================================================================
# MODEL: Task
# =============================================================================

class Task(Base):
    """
    Model zadania.
    
    Obsługuje zarówno zadania główne jak i subtaski (via parent_id).
    Hierarchia: parent_id tworzy drzewo zadań.
    """
    __tablename__ = 'tasks'
    __table_args__ = (
        CheckConstraint('length(title) >= 1 AND length(title) <= 500', name='check_title_length'),
        CheckConstraint('parent_id IS NULL OR parent_id != id', name='check_valid_parent'),
        Index('idx_tasks_user', 'user_id', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_tasks_parent', 'parent_id', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_tasks_status', 'user_id', 'status', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_tasks_updated', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        Index('idx_tasks_deleted', 'deleted_at', postgresql_where=Column('deleted_at').isnot(None)),
        {'schema': 's06_tasks'}
    )
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID/GUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=True)
    
    # Core fields
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Boolean, default=False, nullable=False)  # False=todo, True=done
    
    # Dates
    due_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    alarm_date = Column(DateTime, nullable=True)
    
    # Relations
    note_id = Column(Integer, nullable=True)  # FK do notatek (opcjonalne)
    
    # Custom data (JSON)
    custom_data = Column(JSONB, default={}, nullable=False, server_default='{}')
    
    # Metadata
    archived = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    
    # Sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title[:30]}, status={self.status})>"


# =============================================================================
# MODEL: TaskTag
# =============================================================================

class TaskTag(Base):
    """
    Model tagu zadania.
    
    Tagi są współdzielone między zadaniami użytkownika.
    Relacja M2M przez TaskTagAssignment.
    """
    __tablename__ = 'task_tags'
    __table_args__ = (
        CheckConstraint('length(name) >= 1 AND length(name) <= 100', name='check_tag_name_length'),
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name='check_tag_color_hex'),
        Index('idx_unique_user_tag_name', 'user_id', 'name', unique=True, postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_task_tags_user', 'user_id', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_task_tags_updated', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        {'schema': 's06_tasks'}
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    color = Column(String(7), nullable=False, default='#CCCCCC')
    
    # Sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<TaskTag(id={self.id}, name={self.name}, color={self.color})>"


# =============================================================================
# MODEL: TaskTagAssignment
# =============================================================================

class TaskTagAssignment(Base):
    """
    Relacja M2M między zadaniami a tagami.
    
    Junction table dla many-to-many relationship.
    Brak soft delete - usunięcie jest fizyczne.
    """
    __tablename__ = 'task_tag_assignments'
    __table_args__ = (
        Index('idx_task_tag_assign_task', 'task_id'),
        Index('idx_task_tag_assign_tag', 'tag_id'),
        Index('idx_unique_task_tag', 'task_id', 'tag_id', unique=True),
        {'schema': 's06_tasks'}
    )
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(String, ForeignKey('s06_tasks.task_tags.id', ondelete='CASCADE'), nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<TaskTagAssignment(task_id={self.task_id}, tag_id={self.tag_id})>"


# =============================================================================
# MODEL: TaskCustomList
# =============================================================================

class TaskCustomList(Base):
    """
    Niestandardowe listy wartości (np. priorytety, statusy custom).
    
    Przykład: Lista priorytetów = ["Niski", "Średni", "Wysoki", "Krytyczny"]
    Użytkownik może definiować własne listy dropdown.
    """
    __tablename__ = 'task_custom_lists'
    __table_args__ = (
        CheckConstraint('length(name) >= 1 AND length(name) <= 100', name='check_list_name_length'),
        Index('idx_unique_user_list_name', 'user_id', 'name', unique=True, postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_custom_lists_user', 'user_id', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_custom_lists_updated', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        {'schema': 's06_tasks'}
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    values = Column(JSONB, nullable=False, default=[], server_default='[]')  # Array wartości
    
    # Sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<TaskCustomList(id={self.id}, name={self.name})>"


# =============================================================================
# MODEL: KanbanItem
# =============================================================================

class KanbanItem(Base):
    """
    Pozycja na tablicy Kanban.
    
    Mapuje zadanie (task_id) do kolumny Kanban (column_type).
    Position określa kolejność w kolumnie.
    """
    __tablename__ = 'kanban_items'
    __table_args__ = (
        CheckConstraint(
            "column_type IN ('todo', 'in_progress', 'done', 'on_hold', 'review')", 
            name='check_column_type'
        ),
        Index('idx_unique_user_task_kanban', 'user_id', 'task_id', unique=True, postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_kanban_items_user', 'user_id', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_kanban_items_column', 'user_id', 'column_type', 'position', postgresql_where=Column('deleted_at').is_(None)),
        Index('idx_kanban_items_updated', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        {'schema': 's06_tasks'}
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=False)
    column_type = Column(String(20), nullable=False)  # 'todo', 'in_progress', 'done', etc.
    position = Column(Integer, default=0, nullable=False)
    
    # Sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<KanbanItem(task_id={self.task_id}, column={self.column_type}, pos={self.position})>"


# =============================================================================
# MODEL: KanbanSettings
# =============================================================================

class KanbanSettings(Base):
    """
    Ustawienia tablicy Kanban użytkownika.
    
    Przechowuje preferencje dla widoku Kanban:
    - Widoczne kolumny
    - Kolory kolumn
    - WIP limits
    - Etc.
    """
    __tablename__ = 'kanban_settings'
    __table_args__ = (
        Index('idx_unique_user_kanban_settings', 'user_id', unique=True),
        Index('idx_kanban_settings_user', 'user_id'),
        Index('idx_kanban_settings_updated', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        {'schema': 's06_tasks'}
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    settings = Column(JSONB, nullable=False, default={}, server_default='{}')
    
    # Sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<KanbanSettings(user_id={self.user_id})>"


# =============================================================================
# MODEL: TaskHistory
# =============================================================================

class TaskHistory(Base):
    """
    Historia zmian zadań (audit log).
    
    Loguje wszystkie akcje na zadaniach:
    - created, updated, deleted
    - status_changed, moved, archived
    - tag_added, tag_removed
    """
    __tablename__ = 'task_history'
    __table_args__ = (
        Index('idx_task_history_task', 'task_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_task_history_user', 'user_id', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_task_history_created', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        {'schema': 's06_tasks'}
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=False)
    action_type = Column(String(50), nullable=False)  # 'created', 'updated', 'deleted', etc.
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(JSONB, default={}, server_default='{}')
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<TaskHistory(task_id={self.task_id}, action={self.action_type})>"


# =============================================================================
# MODEL: ColumnsConfig
# =============================================================================

class ColumnsConfig(Base):
    """
    Konfiguracja kolumn widoku zadań.
    
    Synchronizowane między urządzeniami:
    - Widoczność kolumn
    - Kolejność kolumn
    - Sortowanie
    
    NIE synchronizowane (tylko lokalne):
    - Szerokości kolumn
    - Scroll position
    """
    __tablename__ = 'columns_config'
    __table_args__ = (
        Index('idx_unique_user_columns_config', 'user_id', unique=True),
        Index('idx_columns_config_user', 'user_id'),
        Index('idx_columns_config_updated', 'updated_at', postgresql_ops={'updated_at': 'DESC'}),
        {'schema': 's06_tasks'}
    )
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    columns = Column(JSONB, nullable=False, default=[], server_default='[]')
    
    # Sync metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<ColumnsConfig(user_id={self.user_id})>"


# =============================================================================
# Aliases dla kompatybilności
# =============================================================================
TasksSchema = Task
TaskTagsSchema = TaskTag
KanbanItemsSchema = KanbanItem
