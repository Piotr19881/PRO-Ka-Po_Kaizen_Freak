"""
Pomodoro Models - Modele danych dla sesji Pomodoro
Wzorowane na alarm_models.py
"""
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Union
import uuid as uuid_module
from loguru import logger
from .pomodoro_logic import SessionType, SessionStatus


def validate_uuid(value: str, field_name: str = "id") -> str:
    """
    Waliduje czy string jest poprawnym UUID.
    
    Args:
        value: String do walidacji
        field_name: Nazwa pola (dla error message)
        
    Returns:
        value jeśli poprawny UUID
        
    Raises:
        ValueError: jeśli value nie jest poprawnym UUID
    """
    try:
        uuid_module.UUID(value)
        return value
    except (ValueError, AttributeError) as e:
        raise ValueError(f"{field_name} must be a valid UUID, got: {value}") from e


def parse_datetime_field(value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Uniwersalna funkcja do parsowania pól datetime.
    Centralizuje logikę konwersji dat w całym module.
    
    Args:
        value: String ISO, obiekt datetime lub None
        
    Returns:
        datetime object lub None
    """
    if value is None:
        return None
    
    if isinstance(value, datetime):
        return value
    
    if isinstance(value, str):
        try:
            # Handle ISO format with 'Z' (UTC)
            value_clean = value.replace('Z', '+00:00')
            return datetime.fromisoformat(value_clean)
        except (ValueError, AttributeError) as e:
            logger.warning(f"[POMODORO] Failed to parse datetime: {value}, error: {e}")
            return None
    
    return None


@dataclass
class PomodoroTopic:
    """Model tematu sesji Pomodoro"""
    id: str
    user_id: str
    name: str
    color: str = "#FF6B6B"  # Domyślny czerwony
    icon: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Walidacja po utworzeniu obiektu"""
        self.id = validate_uuid(self.id, "id")
        self.user_id = validate_uuid(self.user_id, "user_id")
    
    @property
    def local_id(self) -> str:
        """Alias dla id (dla kompatybilności z sync_manager)"""
        return self.id
    
    def to_dict(self) -> dict:
        """Konwertuj na słownik dla API/DB"""
        return {
            'id': self.id,
            'local_id': self.id,  # Dodaj local_id dla API
            'user_id': self.user_id,
            'name': self.name,
            'color': self.color,
            'icon': self.icon,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'version': self.version,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'PomodoroTopic':
        return PomodoroTopic(
            id=data['id'],
            user_id=data['user_id'],
            name=data['name'],
            color=data.get('color', '#FF6B6B'),
            icon=data.get('icon'),
            description=data.get('description'),
            created_at=parse_datetime_field(data.get('created_at')) or datetime.now(),
            updated_at=parse_datetime_field(data.get('updated_at')),
            deleted_at=parse_datetime_field(data.get('deleted_at')),
        )


@dataclass
class PomodoroSession:
    """
    Model sesji Pomodoro dla DB/Sync (Database/API Model)
    
    JEDNOSTKI CZASU (WAŻNE):
    - planned_duration: MINUTY (np. 25, 5, 15) - zgodne z SessionData
    - actual_work_time: MINUTY (np. 25) - RÓŻNI SIĘ od SessionData!
    - actual_break_time: MINUTY (np. 5) - RÓŻNI SIĘ od SessionData!
    
    UWAGA: SessionData używa SEKUND dla actual_*_time, ale PomodoroSession
    używa MINUT dla kompatybilności z database schema (SQLite + PostgreSQL).
    Konwersja odbywa się w from_session_data() metodzie.
    
    Odpowiednik SessionData z pomodoro_logic.py, rozszerzony o pola DB/sync.
    """
    id: str
    user_id: str
    topic_id: Optional[str]
    topic_name: str
    session_type: SessionType
    status: SessionStatus
    
    # Czasy
    session_date: datetime  # Data sesji (bez czasu)
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    # Długości czasu
    planned_duration: int = 25  # MINUTY planowanego czasu (np. 25)
    actual_work_time: int = 0   # MINUTY rzeczywistego czasu pracy (np. 25)
    actual_break_time: int = 0  # MINUTY rzeczywistego czasu przerwy (np. 5)
    
    # Metadane
    pomodoro_count: int = 0  # Numer pomodoro w cyklu (1-4)
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    productivity_rating: Optional[int] = None  # 1-5
    interruptions_count: int = 0
    
    # Synchronizacja
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    version: int = 1
    needs_sync: bool = True
    
    def __post_init__(self):
        """Walidacja po utworzeniu obiektu"""
        self.id = validate_uuid(self.id, "id")
        self.user_id = validate_uuid(self.user_id, "user_id")
        if self.topic_id:
            self.topic_id = validate_uuid(self.topic_id, "topic_id")
    
    @property
    def local_id(self) -> str:
        """Alias dla id (dla kompatybilności z sync_manager)"""
        return self.id
    
    def to_dict(self) -> dict:
        """Konwertuj na słownik dla API/DB"""
        return {
            'id': self.id,
            'local_id': self.id,  # Dodaj local_id dla API
            'user_id': self.user_id,
            'topic_id': self.topic_id,
            'topic_name': self.topic_name,
            'session_type': self.session_type.value,
            'status': self.status.value,
            'session_date': self.session_date.date().isoformat(),
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            
            # Backend wymaga work_duration zamiast planned_duration
            'work_duration': self.planned_duration,
            'short_break_duration': 5,  # Wartość domyślna
            'long_break_duration': 15,  # Wartość domyślna
            
            'actual_work_time': self.actual_work_time,
            'actual_break_time': self.actual_break_time,
            'pomodoro_count': self.pomodoro_count,
            'notes': self.notes,
            'tags': self.tags if self.tags else [],  # Zawsze lista, nie None
            'productivity_rating': self.productivity_rating,
            
            # Backend wymaga last_modified
            'last_modified': self.updated_at.isoformat() if self.updated_at else self.started_at.isoformat(),
            'version': self.version,
            
            # Dodatkowe pola dla lokalnej bazy
            'interruptions_count': self.interruptions_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'needs_sync': self.needs_sync,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'PomodoroSession':
        return PomodoroSession(
            id=data['id'],
            user_id=data['user_id'],
            topic_id=data.get('topic_id'),
            topic_name=data.get('topic_name', ''),
            session_type=SessionType(data['session_type']),
            status=SessionStatus(data['status']),
            session_date=parse_datetime_field(data.get('session_date')) or datetime.now(),
            started_at=parse_datetime_field(data.get('started_at')) or datetime.now(),
            ended_at=parse_datetime_field(data.get('ended_at')),
            planned_duration=data.get('planned_duration', 25),
            actual_work_time=data.get('actual_work_time', 0),
            actual_break_time=data.get('actual_break_time', 0),
            pomodoro_count=data.get('pomodoro_count', 0),
            notes=data.get('notes'),
            tags=data.get('tags', []),
            productivity_rating=data.get('productivity_rating'),
            interruptions_count=data.get('interruptions_count', 0),
            created_at=parse_datetime_field(data.get('created_at')) or datetime.now(),
            updated_at=parse_datetime_field(data.get('updated_at')),
            deleted_at=parse_datetime_field(data.get('deleted_at')),
            synced_at=parse_datetime_field(data.get('synced_at')),
            version=data.get('version', 1),
            needs_sync=data.get('needs_sync', True),
        )
    
    @staticmethod
    def from_session_data(session_data, user_id: str) -> 'PomodoroSession':
        """
        Konwertuj SessionData (z pomodoro_logic.py) na PomodoroSession (DB model)
        
        WAŻNE - JEDNOSTKI CZASU:
        - SessionData.actual_work_time: SEKUNDY (z pomodoro_logic)
        - PomodoroSession.actual_work_time: MINUTY (database format)
        Konwersja: sekundy // 60 = minuty
        
        Args:
            session_data: Obiekt SessionData z pomodoro_logic
            user_id: ID użytkownika
        
        Returns:
            PomodoroSession gotowy do zapisu w DB
        """
        # FIXED: Używaj actual_work_time z SessionData (w sekundach) i konwertuj na minuty
        # Poprzednio: obliczano ended_at - started_at co gubiło dane przy przerwaniach
        actual_work = session_data.actual_work_time // 60  # sekundy -> minuty
        actual_break = session_data.actual_break_time // 60  # sekundy -> minuty
        
        return PomodoroSession(
            id=session_data.id,
            user_id=user_id,
            topic_id=session_data.topic_id,
            topic_name=session_data.topic_name,
            session_type=session_data.session_type,
            status=session_data.status,
            session_date=session_data.session_date,
            started_at=session_data.started_at,
            ended_at=session_data.ended_at,
            planned_duration=session_data.planned_duration,
            actual_work_time=actual_work,
            actual_break_time=actual_break,
            pomodoro_count=session_data.pomodoro_count,
            notes=session_data.notes,
            tags=session_data.tags,
            productivity_rating=session_data.productivity_rating,
        )
