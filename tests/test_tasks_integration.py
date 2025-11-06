"""
Test integracji synchronizacji Tasks
Testy local-first architecture

Scenariusze:
1. Test offline create → sync_queue entry
2. Test online sync → bulk_sync API call → server DB
3. Test cross-device → WebSocket SYNC_REQUIRED → local DB update
4. Test conflict → last-write-wins → version increment
"""
import sys
import time
import sqlite3
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.Modules.task_module.task_logic import TasksManager
from src.Modules.task_module.task_local_database import TaskLocalDatabase
from loguru import logger

# Setup logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")


def test_1_offline_create():
    """
    Test 1: Offline Create
    - Utwórz TasksManager bez sync (enable_sync=False)
    - Dodaj zadanie
    - Sprawdź czy zadanie jest w tasks.db
    - Sprawdź czy NIE ma w sync_queue (bo sync wyłączony)
    """
    print("\n" + "="*80)
    print("TEST 1: Offline Create (no sync)")
    print("="*80)
    
    # Setup
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    db_path = test_dir / "tasks_test.db"
    
    # Usuń stare dane
    if db_path.exists():
        db_path.unlink()
    
    # Utwórz TasksManager BEZ synchronizacji
    manager = TasksManager(
        data_dir=test_dir,
        enable_sync=False
    )
    
    # Dodaj zadanie
    task_data = {
        'title': 'Test Task - Offline Create',
        'description': 'Test description',
        'status': 'todo'
    }
    
    result = manager.add_task(task_data)
    print(f"✓ Task created: {result}")
    
    assert result is not None, "Task creation failed"
    assert 'id' in result, "Task ID missing"
    assert result['title'] == task_data['title'], "Task title mismatch"
    
    # Sprawdź bazę danych
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Sprawdź czy task jest w tasks table
    cursor.execute("SELECT id, title FROM tasks WHERE id = ?", (result['id'],))
    task_row = cursor.fetchone()
    assert task_row is not None, "Task not found in database"
    print(f"✓ Task in DB: id={task_row[0]}, title={task_row[1]}")
    
    # Sprawdź sync_queue (powinno być puste bo sync wyłączony)
    cursor.execute("SELECT COUNT(*) FROM sync_queue")
    queue_count = cursor.fetchone()[0]
    assert queue_count == 0, f"Sync queue should be empty (sync disabled), but has {queue_count} items"
    print(f"✓ Sync queue empty (as expected): {queue_count} items")
    
    conn.close()
    manager.cleanup()
    
    print("✅ TEST 1 PASSED: Offline create works correctly\n")


def test_2_sync_queue_creation():
    """
    Test 2: Sync Queue Creation
    - Utwórz TasksManager Z sync (enable_sync=True) ale BEZ API połączenia
    - Dodaj zadanie
    - Sprawdź czy zadanie trafiło do sync_queue
    """
    print("\n" + "="*80)
    print("TEST 2: Sync Queue Creation (sync enabled, no network)")
    print("="*80)
    
    # Setup
    test_dir = Path(__file__).parent / "test_data"
    db_path = test_dir / "tasks_test_sync.db"
    
    # Usuń stare dane
    if db_path.exists():
        db_path.unlink()
    
    # Utwórz TasksManager Z synchronizacją (ale API nie działa)
    user_id = str(uuid4())
    manager = TasksManager(
        data_dir=test_dir,
        user_id=user_id,
        api_base_url="http://localhost:9999",  # Non-existent server
        auth_token="fake_token",
        refresh_token="fake_refresh",
        enable_sync=True
    )
    
    # Poczekaj chwilę na inicjalizację sync_manager
    time.sleep(1)
    
    # Dodaj zadanie
    task_data = {
        'title': 'Test Task - Sync Queue',
        'description': 'Should be queued for sync',
        'status': 'todo'
    }
    
    result = manager.add_task(task_data)
    print(f"✓ Task created: {result}")
    
    assert result is not None, "Task creation failed"
    
    # Poczekaj na queue processing
    time.sleep(0.5)
    
    # Sprawdź sync_queue
    conn = sqlite3.connect(test_dir / "tasks.db")  # TasksManager używa tasks.db
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, entity_type, entity_id, action, created_at 
        FROM sync_queue 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    queue_items = cursor.fetchall()
    
    print(f"✓ Sync queue items: {len(queue_items)}")
    for item in queue_items:
        print(f"  - {item[1]} ({item[3]}): {item[2]}")
    
    # Powinien być przynajmniej 1 item (task)
    assert len(queue_items) > 0, "Sync queue is empty (expected task to be queued)"
    
    # Sprawdź czy task jest w queue
    task_in_queue = any(item[1] == 'task' and item[3] == 'upsert' for item in queue_items)
    assert task_in_queue, "Task not found in sync queue"
    print(f"✓ Task found in sync queue")
    
    conn.close()
    manager.cleanup()
    
    print("✅ TEST 2 PASSED: Sync queue creation works correctly\n")


def test_3_database_schema():
    """
    Test 3: Database Schema
    - Sprawdź czy wszystkie wymagane kolumny sync są w tabelach
    """
    print("\n" + "="*80)
    print("TEST 3: Database Schema Validation")
    print("="*80)
    
    # Setup
    test_dir = Path(__file__).parent / "test_data"
    db_path = test_dir / "tasks.db"
    
    if not db_path.exists():
        # Create database
        manager = TasksManager(data_dir=test_dir, enable_sync=False)
        manager.cleanup()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Sprawdź tasks table
    cursor.execute("PRAGMA table_info(tasks)")
    tasks_columns = {row[1] for row in cursor.fetchall()}
    
    required_sync_columns = {'version', 'synced_at', 'server_uuid'}
    
    print(f"✓ Tasks table columns: {len(tasks_columns)}")
    for col in sorted(tasks_columns):
        print(f"  - {col}")
    
    missing = required_sync_columns - tasks_columns
    assert not missing, f"Missing sync columns in tasks table: {missing}"
    print(f"✓ All sync columns present in tasks table")
    
    # Sprawdź sync_queue table
    cursor.execute("PRAGMA table_info(sync_queue)")
    sync_queue_columns = {row[1] for row in cursor.fetchall()}
    
    required_queue_columns = {
        'id', 'entity_type', 'entity_id', 'local_id', 
        'action', 'data', 'created_at', 'retry_count', 'last_error'
    }
    
    print(f"\n✓ Sync queue columns: {len(sync_queue_columns)}")
    for col in sorted(sync_queue_columns):
        print(f"  - {col}")
    
    missing_queue = required_queue_columns - sync_queue_columns
    assert not missing_queue, f"Missing columns in sync_queue table: {missing_queue}"
    print(f"✓ All required columns present in sync_queue table")
    
    conn.close()
    
    print("✅ TEST 3 PASSED: Database schema is correct\n")


def test_4_tasksmanager_initialization():
    """
    Test 4: TasksManager Initialization
    - Sprawdź czy TasksManager inicjalizuje się poprawnie
    - Sprawdź komponenty sync
    """
    print("\n" + "="*80)
    print("TEST 4: TasksManager Initialization")
    print("="*80)
    
    test_dir = Path(__file__).parent / "test_data"
    
    # Test 1: Bez sync
    manager_no_sync = TasksManager(
        data_dir=test_dir,
        enable_sync=False
    )
    
    assert manager_no_sync.local_db is not None, "local_db not initialized"
    assert manager_no_sync.sync_manager is None, "sync_manager should be None (sync disabled)"
    assert manager_no_sync.ws_client is None, "ws_client should be None (sync disabled)"
    assert manager_no_sync.api_client is None, "api_client should be None (sync disabled)"
    print("✓ TasksManager without sync initialized correctly")
    
    manager_no_sync.cleanup()
    
    # Test 2: Z sync
    user_id = str(uuid4())
    manager_with_sync = TasksManager(
        data_dir=test_dir,
        user_id=user_id,
        api_base_url="http://localhost:9999",
        auth_token="test_token",
        refresh_token="test_refresh",
        enable_sync=True
    )
    
    time.sleep(1)  # Poczekaj na inicjalizację
    
    assert manager_with_sync.local_db is not None, "local_db not initialized"
    assert manager_with_sync.sync_manager is not None, "sync_manager not initialized"
    assert manager_with_sync.api_client is not None, "api_client not initialized"
    assert manager_with_sync.ws_client is not None, "ws_client not initialized"
    print("✓ TasksManager with sync initialized correctly")
    
    # Sprawdź czy sync_manager działa
    assert manager_with_sync.sync_manager._is_running, "sync_manager not running"
    print("✓ SyncManager background thread is running")
    
    # Sprawdź stats
    stats = manager_with_sync.get_sync_stats()
    print(f"✓ Sync stats: {stats}")
    assert 'sync_count' in stats, "Sync stats missing sync_count"
    
    manager_with_sync.cleanup()
    
    print("✅ TEST 4 PASSED: TasksManager initialization works correctly\n")


def test_5_load_and_filter_tasks():
    """
    Test 5: Load and Filter Tasks
    - Dodaj kilka zadań
    - Sprawdź load_tasks()
    - Sprawdź filter_tasks()
    """
    print("\n" + "="*80)
    print("TEST 5: Load and Filter Tasks")
    print("="*80)
    
    test_dir = Path(__file__).parent / "test_data"
    db_path = test_dir / "tasks_filter_test.db"
    
    if db_path.exists():
        db_path.unlink()
    
    manager = TasksManager(data_dir=test_dir, enable_sync=False)
    
    # Dodaj kilka zadań
    tasks_data = [
        {'title': 'Task 1 - Active', 'status': 'todo', 'tags': ['urgent']},
        {'title': 'Task 2 - Completed', 'status': 'done', 'tags': ['work']},
        {'title': 'Task 3 - Active Work', 'status': 'todo', 'tags': ['work']},
        {'title': 'Task 4 - Archived', 'status': 'todo', 'archived': True},
    ]
    
    for task_data in tasks_data:
        result = manager.add_task(task_data)
        assert result is not None, f"Failed to create task: {task_data['title']}"
    
    print(f"✓ Created {len(tasks_data)} tasks")
    
    # Test load_tasks
    all_tasks = manager.load_tasks()
    print(f"✓ Loaded {len(all_tasks)} tasks (exclude archived)")
    assert len(all_tasks) == 3, f"Expected 3 tasks (excluding archived), got {len(all_tasks)}"
    
    # Test load_tasks with archived
    all_tasks_with_archived = manager.load_tasks(include_archived=True)
    print(f"✓ Loaded {len(all_tasks_with_archived)} tasks (include archived)")
    assert len(all_tasks_with_archived) == 4, f"Expected 4 tasks (including archived), got {len(all_tasks_with_archived)}"
    
    # Test filter by status
    active_tasks = manager.filter_tasks(status='active')
    print(f"✓ Active tasks: {len(active_tasks)}")
    assert len(active_tasks) == 2, f"Expected 2 active tasks, got {len(active_tasks)}"
    
    completed_tasks = manager.filter_tasks(status='completed')
    print(f"✓ Completed tasks: {len(completed_tasks)}")
    assert len(completed_tasks) == 1, f"Expected 1 completed task, got {len(completed_tasks)}"
    
    # Test filter by text
    work_tasks = manager.filter_tasks(text='work')
    print(f"✓ Tasks with 'work': {len(work_tasks)}")
    assert len(work_tasks) >= 1, f"Expected at least 1 task with 'work', got {len(work_tasks)}"
    
    manager.cleanup()
    
    print("✅ TEST 5 PASSED: Load and filter tasks works correctly\n")


def run_all_tests():
    """Uruchom wszystkie testy"""
    print("\n" + "="*80)
    print("🧪 RUNNING TASKS INTEGRATION TESTS")
    print("="*80)
    
    tests = [
        test_1_offline_create,
        test_2_sync_queue_creation,
        test_3_database_schema,
        test_4_tasksmanager_initialization,
        test_5_load_and_filter_tasks,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ TEST FAILED: {test.__name__}")
            print(f"   Error: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ TEST ERROR: {test.__name__}")
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*80)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    print("="*80)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {failed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
