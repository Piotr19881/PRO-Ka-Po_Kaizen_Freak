"""
SQLAlchemy Models for TeamWork Module
Modele tabel bazy danych dla modułu współpracy zespołowej
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, Date, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from .database import Base


class WorkGroup(Base):
    """Model grupy roboczej"""
    __tablename__ = 'work_groups'
    __table_args__ = {'schema': 's02_teamwork'}
    
    group_id = Column(Integer, primary_key=True, autoincrement=True)
    group_name = Column(String(200), nullable=False)
    description = Column(Text)
    created_by = Column(Text, ForeignKey('s01_user_accounts.users.id'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Sync metadata (Phase 5)
    server_id = Column(Integer, unique=True, index=True)
    last_synced = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(20), default='synced')
    version = Column(Integer, default=1)
    modified_locally = Column(Boolean, default=False)
    
    # Relacje
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="group", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])


class GroupMember(Base):
    """Model członka grupy roboczej"""
    __tablename__ = 'group_members'
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'member')", name='check_role'),
        {'schema': 's02_teamwork'}
    )
    
    group_member_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('s02_teamwork.work_groups.group_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Text, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), nullable=False, default='member')
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relacje
    group = relationship("WorkGroup", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])


class Topic(Base):
    """Model wątku tematycznego"""
    __tablename__ = 'topics'
    __table_args__ = {'schema': 's02_teamwork'}
    
    topic_id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey('s02_teamwork.work_groups.group_id', ondelete='CASCADE'), nullable=False)
    topic_name = Column(String(300), nullable=False)
    created_by = Column(Text, ForeignKey('s01_user_accounts.users.id'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    # Sync metadata (Phase 5)
    server_id = Column(Integer, unique=True, index=True)
    last_synced = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(20), default='synced')
    version = Column(Integer, default=1)
    modified_locally = Column(Boolean, default=False)
    
    # Relacje
    group = relationship("WorkGroup", back_populates="topics")
    creator = relationship("User", foreign_keys=[created_by])
    messages = relationship("Message", back_populates="topic", cascade="all, delete-orphan")
    tasks = relationship("TeamWorkTask", back_populates="topic", cascade="all, delete-orphan")
    files = relationship("TopicFile", back_populates="topic", cascade="all, delete-orphan")


class Message(Base):
    """Model wiadomości w wątku"""
    __tablename__ = 'messages'
    __table_args__ = {'schema': 's02_teamwork'}
    
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('s02_teamwork.topics.topic_id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Text, ForeignKey('s01_user_accounts.users.id'), nullable=False)
    content = Column(Text, nullable=False)
    background_color = Column(String(7), default='#FFFFFF')
    is_important = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    edited_at = Column(TIMESTAMP(timezone=True))
    
    # Sync metadata (Phase 5)
    server_id = Column(Integer, unique=True, index=True)
    last_synced = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(20), default='synced')
    version = Column(Integer, default=1)
    modified_locally = Column(Boolean, default=False)
    
    # Relacje
    topic = relationship("Topic", back_populates="messages")
    author = relationship("User", foreign_keys=[user_id])


class TeamWorkTask(Base):
    """Model zadania w wątku"""
    __tablename__ = 'tasks'
    __table_args__ = {'schema': 's02_teamwork'}
    
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('s02_teamwork.topics.topic_id', ondelete='CASCADE'), nullable=False)
    task_subject = Column(String(500), nullable=False)
    task_description = Column(Text)
    assigned_to = Column(Text, ForeignKey('s01_user_accounts.users.id'))
    created_by = Column(Text, ForeignKey('s01_user_accounts.users.id'), nullable=False)
    due_date = Column(Date)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed = Column(Boolean, default=False)
    completed_by = Column(Text, ForeignKey('s01_user_accounts.users.id'))
    completed_at = Column(TIMESTAMP(timezone=True))
    is_important = Column(Boolean, default=False)
    
    # Sync metadata (Phase 5)
    server_id = Column(Integer, unique=True, index=True)
    last_synced = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(20), default='synced')
    version = Column(Integer, default=1)
    modified_locally = Column(Boolean, default=False)
    
    # Relacje
    topic = relationship("Topic", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])
    completer = relationship("User", foreign_keys=[completed_by])


class TopicFile(Base):
    """Model pliku w wątku - integracja z Backblaze B2"""
    __tablename__ = 'topic_files'
    __table_args__ = {'schema': 's02_teamwork'}
    
    file_id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('s02_teamwork.topics.topic_id', ondelete='CASCADE'), nullable=False)
    file_name = Column(String(500), nullable=False)  # Oryginalna nazwa pliku
    file_size = Column(Integer)  # Rozmiar w bajtach
    content_type = Column(String(200))  # MIME type
    
    # Backblaze B2 identyfikatory
    b2_file_id = Column(String(200), nullable=False)  # ID pliku w B2
    b2_file_name = Column(String(1000), nullable=False)  # Unikalna nazwa w B2
    download_url = Column(String(2000), nullable=False)  # Publiczny URL
    
    # Metadane
    uploaded_by = Column(Text, ForeignKey('s01_user_accounts.users.id'), nullable=False)
    uploaded_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    is_important = Column(Boolean, default=False)
    
    # Sync metadata (Phase 5)
    server_id = Column(Integer, unique=True, index=True)
    last_synced = Column(TIMESTAMP(timezone=True))
    sync_status = Column(String(20), default='synced')
    version = Column(Integer, default=1)
    modified_locally = Column(Boolean, default=False)
    
    # Relacje
    topic = relationship("Topic", back_populates="files")
    uploader = relationship("User", foreign_keys=[uploaded_by])
