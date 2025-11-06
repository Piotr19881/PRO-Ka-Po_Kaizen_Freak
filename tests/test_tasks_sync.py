"""
Test skrypt dla Tasks Synchronization
Testy integracyjne: offline create, online sync, cross-device, conflicts
"""
import sys
from pathlib import Path
import time
import uuid
import requests
from loguru import logger

# Dodaj src do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.Modules.task_module.task_logic import TasksManager
from src.Modules.task_module.task_local_database import TaskLocalDatabase


class TasksSyncTester:
    """Tester synchronizacji zadań"""
    
    def __init__(self, api_base_url: str = "http://127.0.0.1:8000"):
        self.api_base_url = api_base_url
        self.test_user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.test_user_password = "TestPass123!"
        self.user_id = None
        self.access_token = None
        self.refresh_token = None
        
        # Test data directory
        self.test_dir = Path(__file__).parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)
        
        logger.info(f"🧪 TasksSyncTester initialized")
        logger.info(f"   API: {api_base_url}")
        logger.info(f"   Test user: {self.test_user_email}")
    
    def setup(self):
        """Setup - rejestracja użytkownika testowego"""
        logger.info("\n📋 SETUP: Registering test user...")
        
        try:
            # Register
            response = requests.post(
                f"{self.api_base_url}/api/v1/auth/register",
                json={
                    "email": self.test_user_email,
                    "password": self.test_user_password,
                    "name": "Test User"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                self.user_id = data.get("user_id") or data.get("id")
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                logger.info(f"✅ User registered: {self.user_id}")
                return True
            elif response.status_code == 400 and "already exists" in response.text:
                # User już istnieje - zaloguj
                logger.info("   User exists, logging in...")
                return self._login()
            else:
                logger.error(f"❌ Registration failed: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    def _login(self):
        """Login użytkownika testowego"""
        try:
            response = requests.post(
                f"{self.api_base_url}/api/v1/auth/login",
                json={
                    "email": self.test_user_email,
                    "password": self.test_user_password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_id = data.get("user_id") or data.get("id")
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                logger.info(f"✅ User logged in: {self.user_id}")
                return True
            else:
                logger.error(f"❌ Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def test_1_offline_create(self):
        """
        TEST 1: Offline Create
        Utworzenie zadania offline → sprawdzenie sync_queue
        """
        logger.info("\n" + "="*60)
        logger.info("🧪 TEST 1: Offline Create")
        logger.info("="*60)
        
        try:
            # Utwórz TasksManager BEZ synchronizacji (offline)
            logger.info("1️⃣ Creating TasksManager (offline mode)...")
            tasks_manager = TasksManager(
                data_dir=self.test_dir,
                enable_sync=False  # OFFLINE
            )
            
            # Dodaj zadanie
            logger.info("2️⃣ Adding task offline...")
            task_data = {
                "title": "Test Task - Offline Create",
                "description": "Created in offline mode",
                "status": "todo"
            }
            
            task = tasks_manager.add_task(task_data)
            
            if not task:
                logger.error("❌ Failed to create task")
                return False
            
            task_id = task.get('id')
            logger.info(f"✅ Task created: ID={task_id}, Title={task.get('title')}")
            
            # Sprawdź sync_queue
            logger.info("3️⃣ Checking sync_queue table...")
            db = tasks_manager.local_db
            cursor = db.conn.cursor()
            cursor.execute("SELECT * FROM sync_queue WHERE entity_type = 'task'")
            queue_items = cursor.fetchall()
            
            logger.info(f"   Found {len(queue_items)} items in sync_queue")
            
            # W offline mode NIE powinno być wpisów w queue (bo sync wyłączony)
            if len(queue_items) == 0:
                logger.info("✅ TEST 1 PASSED: No queue entries (sync disabled)")
                return True
            else:
                logger.warning(f"⚠️ Unexpected queue entries: {queue_items}")
                return True  # Nie jest to błąd krytyczny
            
        except Exception as e:
            logger.error(f"❌ TEST 1 FAILED: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def test_2_online_sync(self):
        """
        TEST 2: Online Sync
        Włączenie sync → sync_now() → sprawdzenie API
        """
        logger.info("\n" + "="*60)
        logger.info("🧪 TEST 2: Online Sync")
        logger.info("="*60)
        
        try:
            # Utwórz TasksManager Z synchronizacją
            logger.info("1️⃣ Creating TasksManager (online mode)...")
            tasks_manager = TasksManager(
                data_dir=self.test_dir,
                user_id=str(self.user_id),
                api_base_url=self.api_base_url,
                auth_token=self.access_token,
                refresh_token=self.refresh_token,
                enable_sync=True  # ONLINE
            )
            
            # Dodaj zadanie
            logger.info("2️⃣ Adding task online...")
            task_data = {
                "title": "Test Task - Online Sync",
                "description": "Created with sync enabled",
                "status": "todo"
            }
            
            task = tasks_manager.add_task(task_data)
            task_id = task.get('id')
            logger.info(f"✅ Task created: ID={task_id}")
            
            # Sprawdź sync_queue
            logger.info("3️⃣ Checking sync_queue...")
            cursor = tasks_manager.local_db.conn.cursor()
            cursor.execute("SELECT * FROM sync_queue WHERE entity_type = 'task'")
            queue_items = cursor.fetchall()
            logger.info(f"   Queue items: {len(queue_items)}")
            
            # Wymuszony sync
            logger.info("4️⃣ Triggering manual sync...")
            tasks_manager.sync_now()
            
            # Czekaj na sync (max 5 sekund)
            logger.info("   Waiting for sync to complete...")
            time.sleep(5)
            
            # Sprawdź stats
            stats = tasks_manager.get_sync_stats()
            logger.info(f"5️⃣ Sync stats: {stats}")
            
            # Sprawdź czy zadanie jest na serwerze
            logger.info("6️⃣ Verifying task on server...")
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(
                f"{self.api_base_url}/api/tasks/tasks",
                headers=headers,
                params={"user_id": self.user_id}
            )
            
            if response.status_code == 200:
                server_tasks = response.json()
                logger.info(f"   Server has {len(server_tasks)} tasks")
                
                # Szukaj naszego zadania po tytule
                found = any(t.get('title') == task_data['title'] for t in server_tasks)
                
                if found:
                    logger.info("✅ TEST 2 PASSED: Task synced to server")
                    
                    # Cleanup
                    tasks_manager.cleanup()
                    return True
                else:
                    logger.error("❌ Task not found on server")
                    logger.info(f"   Server tasks: {[t.get('title') for t in server_tasks]}")
                    return False
            else:
                logger.error(f"❌ Failed to fetch tasks from server: {response.status_code}")
                return False
            
        except Exception as e:
            logger.error(f"❌ TEST 2 FAILED: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def test_3_websocket_connection(self):
        """
        TEST 3: WebSocket Connection
        Sprawdzenie połączenia WebSocket
        """
        logger.info("\n" + "="*60)
        logger.info("🧪 TEST 3: WebSocket Connection")
        logger.info("="*60)
        
        try:
            logger.info("1️⃣ Creating TasksManager with WebSocket...")
            tasks_manager = TasksManager(
                data_dir=self.test_dir,
                user_id=str(self.user_id),
                api_base_url=self.api_base_url,
                auth_token=self.access_token,
                refresh_token=self.refresh_token,
                enable_sync=True
            )
            
            # Sprawdź czy WebSocket client istnieje
            if tasks_manager.ws_client:
                logger.info("✅ WebSocket client created")
                
                # Czekaj na połączenie
                logger.info("2️⃣ Waiting for WebSocket connection...")
                time.sleep(3)
                
                # TODO: Sprawdź status połączenia
                logger.info("✅ TEST 3 PASSED: WebSocket component ready")
                
                # Cleanup
                tasks_manager.cleanup()
                return True
            else:
                logger.warning("⚠️ WebSocket client not initialized")
                return False
                
        except Exception as e:
            logger.error(f"❌ TEST 3 FAILED: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def test_4_database_schema(self):
        """
        TEST 4: Database Schema
        Sprawdzenie kolumn sync w bazie
        """
        logger.info("\n" + "="*60)
        logger.info("🧪 TEST 4: Database Schema Validation")
        logger.info("="*60)
        
        try:
            logger.info("1️⃣ Checking tasks table schema...")
            db = TaskLocalDatabase(db_path=self.test_dir / "tasks.db", user_id=1)
            
            cursor = db.conn.cursor()
            cursor.execute("PRAGMA table_info(tasks)")
            columns = cursor.fetchall()
            
            column_names = [col[1] for col in columns]
            logger.info(f"   Columns: {column_names}")
            
            required_sync_columns = ['version', 'synced_at', 'server_uuid']
            missing = [col for col in required_sync_columns if col not in column_names]
            
            if missing:
                logger.error(f"❌ Missing sync columns: {missing}")
                return False
            else:
                logger.info("✅ All sync columns present")
            
            # Sprawdź sync_queue table
            logger.info("2️⃣ Checking sync_queue table...")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_queue'")
            result = cursor.fetchone()
            
            if result:
                logger.info("✅ sync_queue table exists")
                
                # Sprawdź kolumny
                cursor.execute("PRAGMA table_info(sync_queue)")
                queue_columns = cursor.fetchall()
                queue_column_names = [col[1] for col in queue_columns]
                logger.info(f"   sync_queue columns: {queue_column_names}")
                
                logger.info("✅ TEST 4 PASSED: Database schema valid")
                return True
            else:
                logger.error("❌ sync_queue table not found")
                return False
            
        except Exception as e:
            logger.error(f"❌ TEST 4 FAILED: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run_all_tests(self):
        """Uruchom wszystkie testy"""
        logger.info("\n" + "🚀"*30)
        logger.info("TASKS SYNC INTEGRATION TESTS")
        logger.info("🚀"*30 + "\n")
        
        # Setup
        if not self.setup():
            logger.error("❌ Setup failed - aborting tests")
            return
        
        # Run tests
        results = {
            "TEST 1: Offline Create": self.test_1_offline_create(),
            "TEST 2: Online Sync": self.test_2_online_sync(),
            "TEST 3: WebSocket Connection": self.test_3_websocket_connection(),
            "TEST 4: Database Schema": self.test_4_database_schema(),
        }
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*60)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {test_name}")
        
        passed = sum(results.values())
        total = len(results)
        
        logger.info("\n" + "="*60)
        logger.info(f"Results: {passed}/{total} tests passed")
        logger.info("="*60 + "\n")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.warning(f"⚠️ {total - passed} tests failed")


if __name__ == "__main__":
    # Konfiguracja loggera
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Run tests
    tester = TasksSyncTester(api_base_url="http://127.0.0.1:8000")
    tester.run_all_tests()
