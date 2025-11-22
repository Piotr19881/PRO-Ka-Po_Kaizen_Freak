"""
Pomodoro Utility Functions
===========================
Helper functions dla modułu Pomodoro.

JEDNOSTKI CZASU:
- SessionData: planned_duration (minuty), actual_*_time (SEKUNDY)
- PomodoroSession: wszystkie czasy w MINUTACH
- Używaj tych funkcji do konwersji między formatami
"""

from typing import Tuple


def minutes_to_seconds(minutes: int) -> int:
    """
    Konwertuj minuty na sekundy.
    
    Args:
        minutes: Liczba minut
        
    Returns:
        Liczba sekund
        
    Example:
        >>> minutes_to_seconds(25)
        1500
    """
    return minutes * 60


def seconds_to_minutes(seconds: int) -> int:
    """
    Konwertuj sekundy na minuty (zaokrąglone w dół).
    
    Args:
        seconds: Liczba sekund
        
    Returns:
        Liczba minut (zaokrąglone w dół)
        
    Example:
        >>> seconds_to_minutes(1500)
        25
        >>> seconds_to_minutes(1559)
        25
    """
    return seconds // 60


def seconds_to_minutes_rounded(seconds: int) -> int:
    """
    Konwertuj sekundy na minuty (zaokrąglone matematycznie).
    
    Args:
        seconds: Liczba sekund
        
    Returns:
        Liczba minut (zaokrąglone)
        
    Example:
        >>> seconds_to_minutes_rounded(1500)
        25
        >>> seconds_to_minutes_rounded(1530)
        26
    """
    return round(seconds / 60)


def format_seconds_to_mmss(seconds: int) -> str:
    """
    Formatuj sekundy do wyświetlenia MM:SS.
    
    Args:
        seconds: Liczba sekund
        
    Returns:
        String w formacie "MM:SS"
        
    Example:
        >>> format_seconds_to_mmss(1500)
        '25:00'
        >>> format_seconds_to_mmss(90)
        '01:30'
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def format_seconds_to_human(seconds: int) -> str:
    """
    Formatuj sekundy do czytelnej formy "X min Y sek".
    
    Args:
        seconds: Liczba sekund
        
    Returns:
        String w formacie "X min Y sek" lub "X min" jeśli bez sekund
        
    Example:
        >>> format_seconds_to_human(1500)
        '25 min'
        >>> format_seconds_to_human(90)
        '1 min 30 sek'
    """
    minutes = seconds // 60
    secs = seconds % 60
    
    if secs == 0:
        return f"{minutes} min"
    elif minutes == 0:
        return f"{secs} sek"
    else:
        return f"{minutes} min {secs} sek"


def parse_mmss_to_seconds(time_str: str) -> int:
    """
    Parsuj string "MM:SS" do sekund.
    
    Args:
        time_str: String w formacie "MM:SS"
        
    Returns:
        Liczba sekund
        
    Raises:
        ValueError: Jeśli format jest nieprawidłowy
        
    Example:
        >>> parse_mmss_to_seconds("25:00")
        1500
        >>> parse_mmss_to_seconds("01:30")
        90
    """
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid format: {time_str}. Expected MM:SS")
        
        minutes = int(parts[0])
        seconds = int(parts[1])
        
        if seconds >= 60:
            raise ValueError(f"Seconds must be < 60, got {seconds}")
        
        return minutes * 60 + seconds
    except (ValueError, IndexError) as e:
        raise ValueError(f"Cannot parse '{time_str}' to seconds: {e}")


def get_time_percentage(elapsed_seconds: int, total_seconds: int) -> float:
    """
    Oblicz procent ukończonego czasu.
    
    Args:
        elapsed_seconds: Upłynięte sekundy
        total_seconds: Całkowity czas w sekundach
        
    Returns:
        Procent (0.0 - 100.0)
        
    Example:
        >>> get_time_percentage(750, 1500)
        50.0
    """
    if total_seconds == 0:
        return 0.0
    return min(100.0, (elapsed_seconds / total_seconds) * 100)


def get_remaining_time(elapsed_seconds: int, total_seconds: int) -> Tuple[int, str]:
    """
    Oblicz pozostały czas.
    
    Args:
        elapsed_seconds: Upłynięte sekundy
        total_seconds: Całkowity czas w sekundach
        
    Returns:
        Tuple (remaining_seconds, formatted_string)
        
    Example:
        >>> get_remaining_time(300, 1500)
        (1200, '20:00')
    """
    remaining = max(0, total_seconds - elapsed_seconds)
    return remaining, format_seconds_to_mmss(remaining)
