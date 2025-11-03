"""
Test demonstracyjny dla PomodoroLogic
====================================
Pokazuje jak używać managera logiki Pomodoro w aplikacji.
"""

from src.Modules.Pomodoro_module import (
    PomodoroLogic,
    PomodoroSettings,
    SessionType,
    SessionStatus,
)


def test_pomodoro_logic():
    """Demonstracja podstawowego użycia PomodoroLogic"""
    
    print("=" * 60)
    print("TEST POMODORO LOGIC - Demonstracja użycia")
    print("=" * 60)
    
    # 1. Utwórz ustawienia
    settings = PomodoroSettings(
        work_duration=25,
        short_break_duration=5,
        long_break_duration=15,
        sessions_count=4,
        auto_start_breaks=True,
        auto_start_pomodoro=False,
        sound_work_end=True,
        sound_break_end=True,
    )
    
    print("\n📋 Ustawienia:")
    print(f"  - Czas pracy: {settings.work_duration} min")
    print(f"  - Krótka przerwa: {settings.short_break_duration} min")
    print(f"  - Długa przerwa: {settings.long_break_duration} min")
    print(f"  - Sesji do długiej przerwy: {settings.sessions_count}")
    print(f"  - Auto-start przerw: {settings.auto_start_breaks}")
    print(f"  - Auto-start sesji: {settings.auto_start_pomodoro}")
    
    # 2. Utwórz manager logiki
    user_id = "test-user-123"
    logic = PomodoroLogic(user_id=user_id, settings=settings)
    
    # 3. Ustaw temat sesji
    logic.set_topic(topic_id="topic-001", topic_name="Nauka Pythona")
    print(f"\n🎯 Temat sesji: {logic.get_current_topic()[1]}")
    
    # 4. Rozpocznij pierwszą sesję roboczą
    print("\n" + "="*60)
    print("SESJA 1: Praca")
    print("="*60)
    
    session = logic.start_new_session()
    print(f"✅ Rozpoczęto sesję: {session.session_type.value}")
    print(f"   ID: {session.id}")
    print(f"   Status: {session.status.value}")
    print(f"   Planowany czas: {session.planned_duration} min")
    print(f"   Rozpoczęto: {session.started_at.strftime('%H:%M:%S')}")
    
    # Symulacja zakończenia sesji (po pełnym czasie)
    actual_seconds = settings.work_duration * 60
    completed = logic.complete_session(actual_seconds)
    print(f"✅ Zakończono sesję: {completed.status.value}")
    print(f"   Rzeczywisty czas pracy: {completed.actual_work_time // 60} min")
    
    # Sprawdź postęp
    progress = logic.get_cycle_progress()
    print(f"📊 Postęp cyklu: {progress[0]}/{progress[1]}")
    
    # Sprawdź co dalej
    next_type = logic.get_next_session_type()
    print(f"⏭️  Następna sesja: {next_type.value}")
    should_auto = logic.should_auto_start_next()
    print(f"🤖 Auto-start: {should_auto}")
    
    # 5. Rozpocznij przerwę (automatycznie krótka, bo to 1. pomodoro)
    print("\n" + "="*60)
    print("SESJA 2: Krótka przerwa")
    print("="*60)
    
    session = logic.start_new_session()
    print(f"✅ Rozpoczęto sesję: {session.session_type.value}")
    print(f"   Planowany czas: {session.planned_duration} min")
    
    # Symulacja pauzy
    logic.pause_session()
    print(f"⏸️  Zapauzowano sesję")
    print(f"   Status: {logic.current_session.status.value}")
    
    # Wznowienie
    logic.resume_session()
    print(f"▶️  Wznowiono sesję")
    print(f"   Status: {logic.current_session.status.value}")
    
    # Zakończenie przerwy
    actual_seconds = settings.short_break_duration * 60
    completed = logic.complete_session(actual_seconds)
    print(f"✅ Zakończono przerwę: {completed.status.value}")
    
    # 6. Symuluj pełny cykl (3 więcej sesji roboczych)
    print("\n" + "="*60)
    print("SYMULACJA PEŁNEGO CYKLU (3 sesje robocze + długa przerwa)")
    print("="*60)
    
    for i in range(3):
        # Sesja robocza
        session = logic.start_new_session()
        print(f"\n📝 Sesja robocza {i+2}/4")
        actual_seconds = settings.work_duration * 60
        logic.complete_session(actual_seconds)
        
        progress = logic.get_cycle_progress()
        print(f"   Postęp: {progress[0]}/{progress[1]}")
        
        # Przerwa (krótka lub długa)
        next_type = logic.get_next_session_type()
        if next_type == SessionType.LONG_BREAK:
            print(f"   ⏭️  Następna: DŁUGA PRZERWA (ukończono cykl!)")
            break
        else:
            session = logic.start_new_session()
            print(f"   ☕ Krótka przerwa...")
            actual_seconds = settings.short_break_duration * 60
            logic.complete_session(actual_seconds)
    
    # Długa przerwa
    print("\n" + "="*60)
    print("SESJA: Długa przerwa (nagroda za pełny cykl!)")
    print("="*60)
    
    session = logic.start_new_session()
    print(f"✅ Rozpoczęto: {session.session_type.value}")
    print(f"   Planowany czas: {session.planned_duration} min")
    actual_seconds = settings.long_break_duration * 60
    completed = logic.complete_session(actual_seconds)
    print(f"✅ Zakończono długą przerwę!")
    
    # 7. Statystyki dzienne
    print("\n" + "="*60)
    print("STATYSTYKI DZIENNE")
    print("="*60)
    
    stats = logic.get_today_stats()
    print(f"📊 Całkowite sesje dziś: {stats['total_sessions']}")
    print(f"🏆 Długie sesje dziś: {stats['long_sessions']}")
    print(f"🔄 Bieżący cykl: {stats['completed_pomodoros']}/{stats['sessions_in_cycle']}")
    
    # 8. Test przerwania sesji
    print("\n" + "="*60)
    print("TEST: Przerwanie sesji")
    print("="*60)
    
    session = logic.start_new_session()
    print(f"✅ Rozpoczęto sesję: {session.session_type.value}")
    
    # Użytkownik przerwał po 10 minutach
    actual_seconds = 10 * 60
    interrupted = logic.interrupt_session(actual_seconds)
    print(f"❌ Sesja przerwana!")
    print(f"   Status: {interrupted.status.value}")
    print(f"   Przepracowano: {interrupted.actual_work_time // 60} min")
    print(f"   ⚠️  Licznik cyklu zresetowany: {logic.completed_pomodoros_in_cycle}")
    
    # 9. Test pominięcia sesji
    print("\n" + "="*60)
    print("TEST: Pominięcie sesji")
    print("="*60)
    
    session = logic.start_new_session()
    print(f"✅ Rozpoczęto sesję: {session.session_type.value}")
    
    skipped = logic.skip_session()
    print(f"⏭️  Sesja pominięta!")
    print(f"   Status: {skipped.status.value}")
    
    # 10. Eksport danych sesji
    print("\n" + "="*60)
    print("EKSPORT DANYCH SESJI (do zapisu w DB)")
    print("="*60)
    
    session = logic.start_new_session()
    actual_seconds = settings.work_duration * 60
    completed = logic.complete_session(actual_seconds)
    
    session_dict = completed.to_dict()
    print(f"📦 Dane sesji jako dict:")
    for key, value in session_dict.items():
        print(f"   {key}: {value}")
    
    # 11. Test konwersji ustawień
    print("\n" + "="*60)
    print("KONWERSJA USTAWIEŃ (do zapisu/odczytu)")
    print("="*60)
    
    settings_dict = settings.to_dict()
    print(f"💾 Ustawienia jako dict:")
    for key, value in settings_dict.items():
        print(f"   {key}: {value}")
    
    # Odtworzenie z dict
    restored_settings = PomodoroSettings.from_dict(settings_dict)
    print(f"\n✅ Przywrócono ustawienia:")
    print(f"   Czas pracy: {restored_settings.work_duration} min")
    
    print("\n" + "="*60)
    print("✅ TEST ZAKOŃCZONY POMYŚLNIE")
    print("="*60)


if __name__ == "__main__":
    test_pomodoro_logic()
