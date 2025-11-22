"""
Pomodoro Logic Manager - Logika biznesowa cyklu Pomodoro
========================================================
Zarządza cyklem sesji Pomodoro, przełączaniem między stanami,
automatycznym/manualnym trybem oraz logiką statystyk.

Główne odpowiedzialności:
- Zarządzanie cyklem sesji (work → short_break → work → ... → long_break)
- Obsługa auto/manual mode
- Logika liczników i statystyk
- Walidacja i przechowywanie ustawień
- Generowanie danych sesji do zapisu
"""

from enum import Enum
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid


class SessionType(Enum):
    """Typy sesji Pomodoro"""
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class SessionStatus(Enum):
    """Statusy sesji"""
    IDLE = "idle"                    # Nie rozpoczęta
    RUNNING = "running"              # W trakcie
    PAUSED = "paused"                # Zapauzowana
    COMPLETED = "completed"          # Zakończona pomyślnie
    INTERRUPTED = "interrupted"      # Przerwana przez użytkownika
    SKIPPED = "skipped"              # Pominięta


@dataclass
class PomodoroSettings:
    """Ustawienia Pomodoro"""
    work_duration: int = 25          # minuty
    short_break_duration: int = 5    # minuty
    long_break_duration: int = 15    # minuty
    sessions_count: int = 4          # ile sesji roboczych do długiej przerwy
    auto_start_breaks: bool = False  # auto-start przerw
    auto_start_pomodoro: bool = False  # auto-start kolejnych sesji roboczych
    sound_work_end: bool = True      # dźwięk po zakończeniu pracy
    sound_break_end: bool = True     # dźwięk po zakończeniu przerwy
    popup_timer: bool = False        # pokazuj popup timer
    
    def get_duration(self, session_type: SessionType) -> int:
        """Zwraca czas trwania dla danego typu sesji (w minutach)"""
        if session_type == SessionType.WORK:
            return self.work_duration
        elif session_type == SessionType.SHORT_BREAK:
            return self.short_break_duration
        elif session_type == SessionType.LONG_BREAK:
            return self.long_break_duration
        return self.work_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje ustawienia do słownika"""
        return {
            'work_duration': self.work_duration,
            'short_break_duration': self.short_break_duration,
            'long_break_duration': self.long_break_duration,
            'sessions_count': self.sessions_count,
            'auto_start_breaks': self.auto_start_breaks,
            'auto_start_pomodoro': self.auto_start_pomodoro,
            'sound_work_end': self.sound_work_end,
            'sound_break_end': self.sound_break_end,
            'popup_timer': self.popup_timer,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PomodoroSettings':
        """Tworzy ustawienia ze słownika"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class SessionData:
    """
    Dane pojedynczej sesji Pomodoro (UI Logic Model)
    
    JEDNOSTKI CZASU (WAŻNE):
    - planned_duration: MINUTY (np. 25, 5, 15)
    - actual_work_time: SEKUNDY (np. 1500 = 25 min) 
    - actual_break_time: SEKUNDY (np. 300 = 5 min)
    
    UWAGA: Niekonsystencja jednostek jest historyczna i pozostaje
    dla kompatybilności z bazą danych. Zobacz pomodoro_models.py
    PomodoroSession.from_session_data() dla konwersji do DB format (minuty).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    topic_id: Optional[str] = None
    topic_name: str = "Ogólna"
    session_type: SessionType = SessionType.WORK
    status: SessionStatus = SessionStatus.IDLE
    
    # Czasy
    session_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    planned_duration: int = 25  # MINUTY (np. 25)
    actual_work_time: int = 0   # SEKUNDY rzeczywistego czasu pracy (np. 1500)
    actual_break_time: int = 0  # SEKUNDY rzeczywistego czasu przerwy (np. 300)
    
    # Metadane
    pomodoro_count: int = 1  # który pomodoro w cyklu (1-4)
    notes: str = ""
    tags: list = field(default_factory=list)
    productivity_rating: Optional[int] = None  # 1-5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'topic_id': self.topic_id,
            'topic_name': self.topic_name,
            'session_type': self.session_type.value,
            'status': self.status.value,
            'session_date': self.session_date.isoformat() if self.session_date else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'planned_duration': self.planned_duration,
            'actual_work_time': self.actual_work_time,
            'actual_break_time': self.actual_break_time,
            'pomodoro_count': self.pomodoro_count,
            'notes': self.notes,
            'tags': self.tags,
            'productivity_rating': self.productivity_rating,
        }


class PomodoroLogic:
    """
    Manager logiki biznesowej cyklu Pomodoro
    
    Odpowiedzialny za:
    - Zarządzanie stanem sesji
    - Przełączanie między typami sesji (work/break)
    - Logikę auto/manual mode
    - Obliczanie statystyk
    - Generowanie danych do zapisu
    """
    
    def __init__(self, user_id: str, settings: Optional[PomodoroSettings] = None):
        """
        Args:
            user_id: ID użytkownika
            settings: Ustawienia Pomodoro (jeśli None, użyje domyślnych)
        """
        self.user_id = user_id
        self.settings = settings or PomodoroSettings()
        
        # Stan bieżącej sesji
        self.current_session: Optional[SessionData] = None
        self.current_topic_id: Optional[str] = None
        self.current_topic_name: str = "Ogólna"
        
        # Liczniki cyklu
        self.completed_pomodoros_in_cycle = 0  # 0-3 (resetuje się po 4)
        self.today_total_sessions = 0
        self.today_long_sessions = 0
        
        # Callbacki (opcjonalne)
        self.on_session_start: Optional[Callable] = None
        self.on_session_end: Optional[Callable[[SessionData], None]] = None
        self.on_cycle_complete: Optional[Callable] = None
        
    # ==================== ZARZĄDZANIE CYKLEM ====================
    
    def start_new_session(self, session_type: Optional[SessionType] = None) -> SessionData:
        """
        Rozpoczyna nową sesję
        
        Args:
            session_type: Typ sesji (jeśli None, automatycznie określi następną)
            
        Returns:
            Dane nowej sesji
        """
        # Jeśli nie podano typu, określ następny w cyklu
        if session_type is None:
            session_type = self._determine_next_session_type()
        
        # Utwórz nową sesję
        self.current_session = SessionData(
            user_id=self.user_id,
            topic_id=self.current_topic_id,
            topic_name=self.current_topic_name,
            session_type=session_type,
            status=SessionStatus.RUNNING,
            session_date=datetime.now(),
            started_at=datetime.now(),
            planned_duration=self.settings.get_duration(session_type),
            pomodoro_count=self.completed_pomodoros_in_cycle + 1 if session_type == SessionType.WORK else 0,
        )
        
        # Wywołaj callback
        if self.on_session_start:
            self.on_session_start()
        
        return self.current_session
    
    def pause_session(self) -> bool:
        """
        Pauzuje bieżącą sesję
        
        Returns:
            True jeśli sesja została zapauzowana, False jeśli nie ma aktywnej sesji
        """
        if not self.current_session or self.current_session.status != SessionStatus.RUNNING:
            return False
        
        self.current_session.status = SessionStatus.PAUSED
        return True
    
    def resume_session(self) -> bool:
        """
        Wznawia zapauzowaną sesję
        
        Returns:
            True jeśli sesja została wznowiona, False jeśli sesja nie była zapauzowana
        """
        if not self.current_session or self.current_session.status != SessionStatus.PAUSED:
            return False
        
        self.current_session.status = SessionStatus.RUNNING
        return True
    
    def complete_session(self, actual_seconds: int) -> SessionData:
        """
        Kończy sesję jako pomyślnie ukończoną
        
        Args:
            actual_seconds: Rzeczywisty czas trwania sesji w sekundach
            
        Returns:
            Dane zakończonej sesji
        """
        if not self.current_session:
            raise ValueError("Brak aktywnej sesji do zakończenia")
        
        # Uzupełnij dane sesji
        self.current_session.status = SessionStatus.COMPLETED
        self.current_session.ended_at = datetime.now()
        
        # Zapisz rzeczywisty czas
        if self.current_session.session_type == SessionType.WORK:
            self.current_session.actual_work_time = actual_seconds
        else:
            self.current_session.actual_break_time = actual_seconds
        
        # Aktualizuj liczniki
        if self.current_session.session_type == SessionType.WORK:
            self.completed_pomodoros_in_cycle += 1
            self.today_total_sessions += 1
            
            # Jeśli ukończono pełny cykl
            if self.completed_pomodoros_in_cycle >= self.settings.sessions_count:
                self.completed_pomodoros_in_cycle = 0
                self.today_long_sessions += 1
                
                if self.on_cycle_complete:
                    self.on_cycle_complete()
        
        # Wywołaj callback
        session_data = self.current_session
        if self.on_session_end:
            self.on_session_end(session_data)
        
        return session_data
    
    def interrupt_session(self, actual_seconds: int) -> SessionData:
        """
        Przerywa sesję (użytkownik kliknął Stop)
        
        Args:
            actual_seconds: Rzeczywisty czas trwania sesji przed przerwaniem w SEKUNDACH
            
        Returns:
            SessionData: Dane przerwanej sesji
        """
        if not self.current_session:
            raise ValueError("Brak aktywnej sesji do przerwania")
        
        self.current_session.status = SessionStatus.INTERRUPTED
        self.current_session.ended_at = datetime.now()
        
        # Zapisz rzeczywisty czas (nawet jeśli niepełny)
        if self.current_session.session_type == SessionType.WORK:
            self.current_session.actual_work_time = actual_seconds
        else:
            self.current_session.actual_break_time = actual_seconds
        
        # Wywołaj callback
        session_data = self.current_session
        if self.on_session_end:
            self.on_session_end(session_data)
        
        # Resetuj licznik (przerwanie = brak pełnego cyklu)
        self.completed_pomodoros_in_cycle = 0
        
        return session_data
    
    def skip_session(self) -> SessionData:
        """
        Pomija bieżącą sesję (użytkownik kliknął Skip)
        
        Returns:
            Dane pominiętej sesji
        """
        if not self.current_session:
            raise ValueError("Brak aktywnej sesji do pominięcia")
        
        self.current_session.status = SessionStatus.SKIPPED
        self.current_session.ended_at = datetime.now()
        
        # Wywołaj callback
        session_data = self.current_session
        if self.on_session_end:
            self.on_session_end(session_data)
        
        # Nie zwiększaj liczników przy skip
        
        return session_data
    
    def reset_session(self) -> bool:
        """
        Resetuje timer bieżącej sesji (nie zmienia stanu)
        
        Returns:
            True jeśli reset powiódł się
        """
        if not self.current_session:
            return False
        
        # Reset tylko czasu rozpoczęcia (jakby zaczęła się od nowa)
        self.current_session.started_at = datetime.now()
        return True
    
    # ==================== LOGIKA AUTO/MANUAL MODE ====================
    
    def should_auto_start_next(self) -> bool:
        """
        Sprawdza czy następna sesja powinna wystartować automatycznie
        
        Returns:
            True jeśli należy auto-startować następną sesję
        """
        if not self.current_session:
            return False
        
        next_type = self._determine_next_session_type()
        
        # Auto-start przerw
        if next_type in [SessionType.SHORT_BREAK, SessionType.LONG_BREAK]:
            return self.settings.auto_start_breaks
        
        # Auto-start kolejnych sesji roboczych
        if next_type == SessionType.WORK:
            return self.settings.auto_start_pomodoro
        
        return False
    
    def get_next_session_type(self) -> SessionType:
        """
        Zwraca typ następnej sesji (bez uruchamiania)
        
        Returns:
            Typ następnej sesji w cyklu
        """
        return self._determine_next_session_type()
    
    def _determine_next_session_type(self) -> SessionType:
        """
        Określa typ następnej sesji w cyklu
        
        Returns:
            Typ następnej sesji
        """
        # Jeśli brak bieżącej sesji, zacznij od pracy
        if not self.current_session:
            return SessionType.WORK
        
        current_type = self.current_session.session_type
        
        # Po sesji roboczej
        if current_type == SessionType.WORK:
            # Sprawdź czy pora na długą przerwę
            if self.completed_pomodoros_in_cycle >= self.settings.sessions_count:
                return SessionType.LONG_BREAK
            else:
                return SessionType.SHORT_BREAK
        
        # Po krótkiej przerwie → praca
        elif current_type == SessionType.SHORT_BREAK:
            return SessionType.WORK
        
        # Po długiej przerwie → praca (nowy cykl)
        elif current_type == SessionType.LONG_BREAK:
            return SessionType.WORK
        
        return SessionType.WORK
    
    # ==================== ZARZĄDZANIE TEMATEM ====================
    
    def set_topic(self, topic_id: Optional[str], topic_name: str):
        """
        Ustawia temat sesji (możliwe tylko gdy sesja nie jest aktywna)
        
        Args:
            topic_id: ID tematu (może być None dla "Ogólna")
            topic_name: Nazwa tematu
            
        Returns:
            True jeśli temat został ustawiony
        """
        if self.current_session and self.current_session.status == SessionStatus.RUNNING:
            return False  # Nie można zmieniać tematu podczas aktywnej sesji
        
        self.current_topic_id = topic_id
        self.current_topic_name = topic_name
        return True
    
    def get_current_topic(self) -> tuple[Optional[str], str]:
        """
        Zwraca bieżący temat sesji
        
        Returns:
            (topic_id, topic_name)
        """
        return (self.current_topic_id, self.current_topic_name)
    
    # ==================== STATYSTYKI ====================
    
    def get_cycle_progress(self) -> tuple[int, int]:
        """
        Zwraca postęp w bieżącym cyklu
        
        Returns:
            (ukończone_pomodoros, całkowite_w_cyklu)
        """
        return (self.completed_pomodoros_in_cycle, self.settings.sessions_count)
    
    def get_today_stats(self) -> Dict[str, int]:
        """
        Zwraca statystyki dzisiejsze
        
        Returns:
            Słownik ze statystykami
        """
        return {
            'total_sessions': self.today_total_sessions,
            'long_sessions': self.today_long_sessions,
            'completed_pomodoros': self.completed_pomodoros_in_cycle,
            'sessions_in_cycle': self.settings.sessions_count,
        }
    
    def reset_daily_stats(self):
        """Resetuje statystyki dzienne (wywołać o północy)"""
        self.today_total_sessions = 0
        self.today_long_sessions = 0
    
    # ==================== USTAWIENIA ====================
    
    def update_settings(self, new_settings: PomodoroSettings):
        """
        Aktualizuje ustawienia Pomodoro
        
        Args:
            new_settings: Nowe ustawienia
        """
        self.settings = new_settings
    
    def get_settings(self) -> PomodoroSettings:
        """
        Zwraca bieżące ustawienia
        
        Returns:
            Obiekt ustawień
        """
        return self.settings
    
    # ==================== POMOCNICZE ====================
    
    def get_session_duration_seconds(self, session_type: Optional[SessionType] = None) -> int:
        """
        Zwraca planowany czas trwania sesji w sekundach
        
        Args:
            session_type: Typ sesji (jeśli None, użyje bieżącego)
            
        Returns:
            Czas w sekundach
        """
        if session_type is None:
            session_type = self.current_session.session_type if self.current_session else SessionType.WORK
        
        return self.settings.get_duration(session_type) * 60
    
    def is_session_active(self) -> bool:
        """
        Sprawdza czy jest aktywna sesja
        
        Returns:
            True jeśli sesja jest w trakcie lub zapauzowana
        """
        if not self.current_session:
            return False
        
        return self.current_session.status in [SessionStatus.RUNNING, SessionStatus.PAUSED]
    
    def get_current_session_type(self) -> Optional[SessionType]:
        """
        Zwraca typ bieżącej sesji
        
        Returns:
            Typ sesji lub None jeśli brak aktywnej
        """
        return self.current_session.session_type if self.current_session else None
    
    def get_current_session_data(self) -> Optional[SessionData]:
        """
        Zwraca dane bieżącej sesji
        
        Returns:
            Obiekt SessionData lub None
        """
        return self.current_session
