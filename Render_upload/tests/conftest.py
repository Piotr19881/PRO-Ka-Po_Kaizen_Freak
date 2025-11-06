"""
Pytest fixtures for Tasks API tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from app.main import app
from app.database import Base, get_db
from app.auth import create_access_token


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///./test_tasks.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    """Test user data"""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com"
    }


@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers with valid JWT"""
    token = create_access_token(
        data={"user_id": test_user["user_id"], "email": test_user["email"]}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_task(test_user):
    """Sample task data for testing"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": test_user["user_id"],
        "title": "Test Task",
        "description": "This is a test task",
        "status": False,
        "parent_id": None,
        "due_date": None,
        "completion_date": None,
        "alarm_date": None,
        "note_id": None,
        "custom_data": {},
        "archived": False,
        "order": 0,
        "version": 1
    }


@pytest.fixture
def sample_tag(test_user):
    """Sample tag data for testing"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": test_user["user_id"],
        "name": "Test Tag",
        "color": "#FF5733",
        "version": 1
    }


@pytest.fixture
def sample_kanban_item(test_user):
    """Sample Kanban item data for testing"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": test_user["user_id"],
        "task_id": str(uuid.uuid4()),
        "column_type": "todo",
        "position": 0,
        "version": 1
    }


@pytest.fixture
def sample_custom_list(test_user):
    """Sample custom list data for testing"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": test_user["user_id"],
        "name": "Test List",
        "values": ["value1", "value2", "value3"],
        "version": 1
    }
