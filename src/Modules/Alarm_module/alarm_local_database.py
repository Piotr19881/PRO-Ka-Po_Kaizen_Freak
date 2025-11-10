"""
Local Database Module - SQLite Local-First Storage
Lokalna baza danych dla alarmów i timerów z obsługą offline
Unified approach - jedna tabela dla alarmów i timerów
"""
import sqlite3
from pathlib import Path
from datetime import datetime, time
from typing import List, Optional, Dict, Any
from dataclasses import asdict
from loguru import logger
import json

from .alarm_models import Alarm, Timer, AlarmRecurrence


class LocalDatabase:
    """
    Lokalna baza danych SQLite dla local-first architecture
    Przechowuje alarmy i timery offline z możliwością synchronizacji
    Unified approach - jedna tabela dla obu typów
    """
    
    def __init__(self, db_path: Path):
        """
        Inicjalizacja lokalnej bazy danych
        
        Args:
            db_path: Ścieżka do pliku bazy SQLite
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Utwórz połączenie z bazą danych"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Wyniki jako słowniki
        return conn
    
    def _init_database(self):
        """Inicjalizuj strukturę bazy danych - unified table"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Unified table dla alarmów i timerów
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alarms_timers (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    type TEXT NOT NULL,
                    
                    -- Wspólne pola
                    label TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    play_sound INTEGER DEFAULT 1,
                    show_popup INTEGER DEFAULT 1,
                    custom_sound TEXT,
                    
                    -- Pola specyficzne dla alarmów
                    alarm_time TEXT,
                    recurrence TEXT,
                    days TEXT DEFAULT '[]',
                    
                    -- Pola specyficzne dla timerów
                    duration INTEGER,
                    remaining INTEGER,
                    repeat INTEGER,
                    started_at TEXT,
                    
                    -- Synchronizacja
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    deleted_at TEXT,
                    synced_at TEXT,
                    version INTEGER DEFAULT 1,
                    needs_sync INTEGER DEFAULT 1,
                    
                    CHECK (type IN ('alarm', 'timer'))
                )
            """)
            
            # Tabela kolejki synchronizacji
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    
                    CHECK (entity_type IN ('alarm', 'timer')),
                    CHECK (action IN ('upsert', 'delete'))
                )
            """)
            
            # Indeksy
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarms_timers_user ON alarms_timers(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarms_timers_type ON alarms_timers(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarms_timers_sync ON alarms_timers(needs_sync)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_queue ON sync_queue(entity_type, entity_id)")
            
            conn.commit()
            logger.info(f"Local database initialized at {self.db_path}")
    
    # =========================================================================
    # OPERACJE NA ALARMACH
    # =========================================================================
    
    def save_alarm(self, alarm: Alarm, user_id: Optional[str] = None, *, enqueue: bool = True) -> bool:
        """
        Zapisz alarm do lokalnej bazy (unified table)
        
        Args:
            alarm: Obiekt alarmu
            user_id: ID użytkownika (opcjonalne)
        
        Returns:
            True jeśli sukces
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                version = getattr(alarm, 'version', 1)
                
                needs_sync_flag = 1 if enqueue else 0
                synced_at_value = None if enqueue else now

                cursor.execute("""
                    INSERT OR REPLACE INTO alarms_timers 
                    (id, user_id, type, label, enabled, 
                     alarm_time, recurrence, days, 
                     play_sound, show_popup, custom_sound, 
                     created_at, updated_at, synced_at, version, needs_sync)
                    VALUES (?, ?, 'alarm', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alarm.id,
                    user_id,
                    alarm.label,
                    int(alarm.enabled),
                    alarm.time.strftime('%H:%M'),
                    alarm.recurrence.value,
                    json.dumps(alarm.days),
                    int(alarm.play_sound),
                    int(alarm.show_popup),
                    alarm.custom_sound,
                    alarm.created_at.isoformat() if alarm.created_at else now,
                    now,
                    synced_at_value,
                    version,
                    needs_sync_flag
                ))
                
                if enqueue:
                    # Dodaj do kolejki synchronizacji tylko dla zmian lokalnych
                    self._add_to_sync_queue(conn, 'alarm', alarm.id, 'upsert', {
                        'id': alarm.id,
                        'type': 'alarm',
                        'label': alarm.label,
                        'enabled': alarm.enabled,
                        'alarm_time': alarm.time.strftime('%H:%M'),
                        'recurrence': alarm.recurrence.value,
                        'days': alarm.days,
                        'play_sound': alarm.play_sound,
                        'show_popup': alarm.show_popup,
                        'custom_sound': alarm.custom_sound
                    })
                
                conn.commit()
                logger.debug(f"Alarm saved locally: {alarm.id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save alarm locally: {e}")
            return False
    
    def get_alarm(self, alarm_id: str) -> Optional[Alarm]:
        """Pobierz alarm po ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM alarms_timers 
                    WHERE id = ? AND type = 'alarm' AND deleted_at IS NULL
                """, (alarm_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_alarm(dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Failed to get alarm: {e}")
            return None
    
    def get_all_alarms(self, user_id: Optional[str] = None) -> List[Alarm]:
        """Pobierz wszystkie aktywne alarmy"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    cursor.execute("""
                        SELECT * FROM alarms_timers 
                        WHERE user_id = ? AND type = 'alarm' AND deleted_at IS NULL
                        ORDER BY alarm_time
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT * FROM alarms_timers 
                        WHERE type = 'alarm' AND deleted_at IS NULL
                        ORDER BY alarm_time
                    """)
                
                return [self._row_to_alarm(dict(row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get alarms: {e}")
            return []
    
    def delete_alarm(self, alarm_id: str, soft: bool = True) -> bool:
        """
        Usuń alarm (soft delete domyślnie dla synchronizacji)
        
        Args:
            alarm_id: ID alarmu
            soft: Czy soft delete (True) czy hard delete (False)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if soft:
                    # Soft delete - oznacz jako usunięty
                    cursor.execute("""
                        UPDATE alarms_timers 
                        SET deleted_at = ?, updated_at = ?, needs_sync = 1, version = version + 1
                        WHERE id = ? AND type = 'alarm'
                    """, (datetime.now().isoformat(), datetime.now().isoformat(), alarm_id))
                    
                    self._add_to_sync_queue(conn, 'alarm', alarm_id, 'delete', None)
                else:
                    # Hard delete - usuń z bazy
                    cursor.execute("DELETE FROM alarms_timers WHERE id = ? AND type = 'alarm'", (alarm_id,))
                
                conn.commit()
                logger.debug(f"Alarm deleted (soft={soft}): {alarm_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete alarm: {e}")
            return False
    
    def get_unsynced_alarms(self) -> List[Alarm]:
        """Pobierz alarmy wymagające synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM alarms_timers 
                    WHERE type = 'alarm' AND needs_sync = 1
                """)
                
                return [self._row_to_alarm(dict(row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get unsynced alarms: {e}")
            return []
    
    def mark_alarm_synced(self, alarm_id: str) -> bool:
        """Oznacz alarm jako zsynchronizowany"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alarms_timers 
                    SET synced_at = ?, needs_sync = 0
                    WHERE id = ? AND type = 'alarm'
                """, (datetime.now().isoformat(), alarm_id))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark alarm as synced: {e}")
            return False
    
    def update_alarm_version(self, alarm_id: str, version: int) -> bool:
        """Zaktualizuj wersję alarmu po synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alarms_timers 
                    SET version = ?
                    WHERE id = ? AND type = 'alarm'
                """, (version, alarm_id))
                conn.commit()
                logger.debug(f"Updated alarm {alarm_id} to version {version}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update alarm version: {e}")
            return False
    
    # =========================================================================
    # OPERACJE NA TIMERACH
    # =========================================================================
    
    def save_timer(self, timer: Timer, user_id: Optional[str] = None, *, enqueue: bool = True) -> bool:
        """
        Zapisz timer do lokalnej bazy (unified table)
        
        Args:
            timer: Obiekt timera
            user_id: ID użytkownika (opcjonalne)
        
        Returns:
            True jeśli sukces
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                version = getattr(timer, 'version', 1)
                
                needs_sync_flag = 1 if enqueue else 0
                synced_at_value = None if enqueue else now

                cursor.execute("""
                    INSERT OR REPLACE INTO alarms_timers 
                    (id, user_id, type, label, enabled, 
                     duration, remaining, repeat, started_at,
                     play_sound, show_popup, custom_sound, 
                     created_at, updated_at, synced_at, version, needs_sync)
                    VALUES (?, ?, 'timer', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timer.id,
                    user_id,
                    timer.label,
                    int(timer.enabled),
                    timer.duration,
                    timer.remaining,
                    int(timer.repeat),
                    timer.started_at.isoformat() if timer.started_at else None,
                    int(timer.play_sound),
                    int(timer.show_popup),
                    timer.custom_sound,
                    timer.created_at.isoformat() if timer.created_at else now,
                    now,
                    synced_at_value,
                    version,
                    needs_sync_flag
                ))
                
                if enqueue:
                    # Dodaj do kolejki synchronizacji dla zmian lokalnych
                    self._add_to_sync_queue(conn, 'timer', timer.id, 'upsert', {
                        'id': timer.id,
                        'type': 'timer',
                        'label': timer.label,
                        'enabled': timer.enabled,
                        'duration': timer.duration,
                        'remaining': timer.remaining,
                        'repeat': timer.repeat,
                        'started_at': timer.started_at.isoformat() if timer.started_at else None,
                        'play_sound': timer.play_sound,
                        'show_popup': timer.show_popup,
                        'custom_sound': timer.custom_sound
                    })
                
                conn.commit()
                logger.debug(f"Timer saved locally: {timer.id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save timer locally: {e}")
            return False
    
    def get_timer(self, timer_id: str) -> Optional[Timer]:
        """Pobierz timer po ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM alarms_timers 
                    WHERE id = ? AND type = 'timer' AND deleted_at IS NULL
                """, (timer_id,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_timer(dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Failed to get timer: {e}")
            return None
    
    def get_all_timers(self, user_id: Optional[str] = None) -> List[Timer]:
        """Pobierz wszystkie aktywne timery"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if user_id:
                    cursor.execute("""
                        SELECT * FROM alarms_timers 
                        WHERE user_id = ? AND type = 'timer' AND deleted_at IS NULL
                        ORDER BY created_at DESC
                    """, (user_id,))
                else:
                    cursor.execute("""
                        SELECT * FROM alarms_timers 
                        WHERE type = 'timer' AND deleted_at IS NULL
                        ORDER BY created_at DESC
                    """)
                
                return [self._row_to_timer(dict(row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get timers: {e}")
            return []
    
    def delete_timer(self, timer_id: str, soft: bool = True) -> bool:
        """
        Usuń timer (soft delete domyślnie dla synchronizacji)
        
        Args:
            timer_id: ID timera
            soft: Czy soft delete (True) czy hard delete (False)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if soft:
                    # Soft delete - oznacz jako usunięty
                    cursor.execute("""
                        UPDATE alarms_timers 
                        SET deleted_at = ?, updated_at = ?, needs_sync = 1, version = version + 1
                        WHERE id = ? AND type = 'timer'
                    """, (datetime.now().isoformat(), datetime.now().isoformat(), timer_id))
                    
                    self._add_to_sync_queue(conn, 'timer', timer_id, 'delete', None)
                else:
                    # Hard delete - usuń z bazy
                    cursor.execute("DELETE FROM alarms_timers WHERE id = ? AND type = 'timer'", (timer_id,))
                
                conn.commit()
                logger.debug(f"Timer deleted (soft={soft}): {timer_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete timer: {e}")
            return False
    
    def get_unsynced_timers(self) -> List[Timer]:
        """Pobierz timery wymagające synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM alarms_timers 
                    WHERE type = 'timer' AND needs_sync = 1
                """)
                
                return [self._row_to_timer(dict(row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get unsynced timers: {e}")
            return []
    
    def mark_timer_synced(self, timer_id: str) -> bool:
        """Oznacz timer jako zsynchronizowany"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alarms_timers 
                    SET synced_at = ?, needs_sync = 0
                    WHERE id = ? AND type = 'timer'
                """, (datetime.now().isoformat(), timer_id))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark timer as synced: {e}")
            return False
    
    def update_timer_version(self, timer_id: str, version: int) -> bool:
        """Zaktualizuj wersję timera po synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE alarms_timers 
                    SET version = ?
                    WHERE id = ? AND type = 'timer'
                """, (version, timer_id))
                conn.commit()
                logger.debug(f"Updated timer {timer_id} to version {version}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update timer version: {e}")
            return False
    
    # =========================================================================
    # KOLEJKA SYNCHRONIZACJI
    # =========================================================================
    
    def _add_to_sync_queue(self, conn: sqlite3.Connection, entity_type: str, 
                           entity_id: str, action: str, data: Optional[Dict] = None):
        """Dodaj operację do kolejki synchronizacji"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sync_queue (entity_type, entity_id, action, data, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            entity_type,
            entity_id,
            action,
            json.dumps(data) if data else None,
            datetime.now().isoformat()
        ))
    
    def get_sync_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Pobierz elementy z kolejki synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sync_queue 
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get sync queue: {e}")
            return []
    
    def remove_from_sync_queue(self, queue_id: int) -> bool:
        """Usuń element z kolejki synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sync_queue WHERE id = ?", (queue_id,))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove from sync queue: {e}")
            return False
    
    def update_sync_queue_error(self, queue_id: int, error: str) -> bool:
        """Zaktualizuj błąd w kolejce synchronizacji"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_queue 
                    SET retry_count = retry_count + 1, last_error = ?
                    WHERE id = ?
                """, (error, queue_id))
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update sync queue error: {e}")
            return False
    
    # =========================================================================
    # POMOCNICZE METODY KONWERSJI
    # =========================================================================
    
    def _row_to_alarm(self, row: Dict[str, Any]) -> Alarm:
        """
        Konwertuj wiersz bazy na obiekt Alarm
        
        Note: Metadane synchronizacji (version, synced_at, needs_sync) są
        przechowywane w bazie, ale nie są częścią obiektu Alarm.
        """
        time_parts = row['alarm_time'].split(':')
        
        alarm = Alarm(
            id=row['id'],
            time=time(int(time_parts[0]), int(time_parts[1])),
            label=row['label'],
            enabled=bool(row['enabled']),
            recurrence=AlarmRecurrence(row['recurrence']),
            days=json.loads(row['days']),
            play_sound=bool(row['play_sound']),
            show_popup=bool(row['show_popup']),
            custom_sound=row.get('custom_sound'),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now()
        )
        
        # Sync metadata pozostaje w bazie, nie jest częścią obiektu domenowego
        # version, synced_at, needs_sync są używane tylko przez LocalDatabase
        
        return alarm
    
    def _row_to_timer(self, row: Dict[str, Any]) -> Timer:
        """
        Konwertuj wiersz bazy na obiekt Timer
        
        Note: Metadane synchronizacji (version, synced_at, needs_sync) są
        przechowywane w bazie, ale nie są częścią obiektu Timer.
        """
        timer = Timer(
            id=row['id'],
            duration=row['duration'],
            label=row['label'],
            enabled=bool(row['enabled']),
            remaining=row.get('remaining'),
            play_sound=bool(row['play_sound']),
            show_popup=bool(row['show_popup']),
            repeat=bool(row['repeat']),
            custom_sound=row.get('custom_sound'),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else datetime.now(),
            started_at=datetime.fromisoformat(row['started_at']) if row.get('started_at') else None
        )
        
        # Sync metadata pozostaje w bazie, nie jest częścią obiektu domenowego
        # version, synced_at, needs_sync są używane tylko przez LocalDatabase
        
        return timer
    
    # =========================================================================
    # OPERACJE MASOWE
    # =========================================================================
    
    def bulk_import_alarms(self, alarms: List[Alarm], user_id: Optional[str] = None, *, enqueue: bool = False) -> int:
        """
        Import wielu alarmów naraz (np. podczas synchronizacji)
        
        Returns:
            Liczba zaimportowanych alarmów
        """
        count = 0
        for alarm in alarms:
            if self.save_alarm(alarm, user_id, enqueue=enqueue):
                count += 1
        return count
    
    def bulk_import_timers(self, timers: List[Timer], user_id: Optional[str] = None, *, enqueue: bool = False) -> int:
        """
        Import wielu timerów naraz (np. podczas synchronizacji)
        
        Returns:
            Liczba zaimportowanych timerów
        """
        count = 0
        for timer in timers:
            if self.save_timer(timer, user_id, enqueue=enqueue):
                count += 1
        return count
    
    def clear_all_data(self) -> bool:
        """Wyczyść wszystkie dane (UWAGA: Użyj ostrożnie!)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM alarms")
                cursor.execute("DELETE FROM timers")
                cursor.execute("DELETE FROM sync_queue")
                conn.commit()
                logger.warning("All local data cleared!")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            return False
