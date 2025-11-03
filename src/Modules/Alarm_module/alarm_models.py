"""
Alarm Models - Modele danych dla alarmów i timerów
"""
from datetime import datetime, time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AlarmRecurrence(Enum):
    """Cykliczność alarmu"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKDAYS = "weekdays"
    WEEKENDS = "weekends"
    CUSTOM = "custom"


@dataclass
class Alarm:
    """Model alarmu"""
    id: str
    time: time
    label: str
    enabled: bool = True
    recurrence: AlarmRecurrence = AlarmRecurrence.ONCE
    days: list[int] = field(default_factory=list)  # 0=Pon, 1=Wt, ..., 6=Niedz
    play_sound: bool = True
    show_popup: bool = True
    custom_sound: Optional[str] = None  # Ścieżka do niestandardowego dźwięku
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'time': self.time.strftime('%H:%M'),
            'label': self.label,
            'enabled': self.enabled,
            'recurrence': self.recurrence.value,
            'days': self.days,
            'play_sound': self.play_sound,
            'show_popup': self.show_popup,
            'custom_sound': self.custom_sound,
            'created_at': self.created_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Alarm':
        """Utwórz z słownika"""
        # Obsługuj zarówno 'time' (z aplikacji) jak i 'alarm_time' (z serwera)
        time_str = data.get('time') or data.get('alarm_time')
        if not time_str:
            raise ValueError("Missing time/alarm_time in alarm data")
        
        # Parse time string to time object
        if isinstance(time_str, str):
            time_parts = time_str.split(':')
            alarm_time = time(int(time_parts[0]), int(time_parts[1]))
        else:
            # Already a time object
            alarm_time = time_str
        
        return Alarm(
            id=data['id'],
            time=alarm_time,
            label=data['label'],
            enabled=data.get('enabled', True),
            recurrence=AlarmRecurrence(data.get('recurrence', 'once')),
            days=data.get('days', []),
            play_sound=data.get('play_sound', True),
            show_popup=data.get('show_popup', True),
            custom_sound=data.get('custom_sound'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
        )


@dataclass
class Timer:
    """Model timera"""
    id: str
    duration: int  # w sekundach
    label: str
    enabled: bool = False
    remaining: Optional[int] = None  # pozostały czas w sekundach
    play_sound: bool = True
    show_popup: bool = True
    repeat: bool = False
    custom_sound: Optional[str] = None  # Ścieżka do niestandardowego dźwięku
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Konwertuj na słownik"""
        return {
            'id': self.id,
            'duration': self.duration,
            'label': self.label,
            'enabled': self.enabled,
            'remaining': self.remaining,
            'play_sound': self.play_sound,
            'show_popup': self.show_popup,
            'repeat': self.repeat,
            'custom_sound': self.custom_sound,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Timer':
        """Utwórz z słownika"""
        return Timer(
            id=data['id'],
            duration=data['duration'],
            label=data['label'],
            enabled=data.get('enabled', False),
            remaining=data.get('remaining'),
            play_sound=data.get('play_sound', True),
            show_popup=data.get('show_popup', True),
            repeat=data.get('repeat', False),
            custom_sound=data.get('custom_sound'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None
        )
