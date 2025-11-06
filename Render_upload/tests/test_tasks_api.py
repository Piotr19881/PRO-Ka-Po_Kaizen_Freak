"""
Unit tests for Tasks API endpoints
Tests: CRUD operations, conflict handling, bulk sync
"""
import pytest
from fastapi import status
import uuid


class TestTaskCRUD:
    """Test Task CRUD operations"""
    
    def test_create_task(self, client, auth_headers, sample_task):
        """Test creating a new task"""
        response = client.post(
            "/api/tasks/task",
            json=sample_task,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_task["id"]
        assert data["title"] == sample_task["title"]
        assert data["version"] == 1
        assert data["deleted_at"] is None
    
    def test_update_task(self, client, auth_headers, sample_task):
        """Test updating an existing task"""
        # Create task
        client.post("/api/tasks/task", json=sample_task, headers=auth_headers)
        
        # Update task
        updated_task = sample_task.copy()
        updated_task["title"] = "Updated Task Title"
        updated_task["version"] = 1
        
        response = client.post(
            "/api/tasks/task",
            json=updated_task,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Task Title"
        assert data["version"] == 2  # Version incremented
    
    def test_conflict_detection(self, client, auth_headers, sample_task):
        """Test version conflict detection"""
        # Create task
        client.post("/api/tasks/task", json=sample_task, headers=auth_headers)
        
        # Try to update with old version
        conflicting_task = sample_task.copy()
        conflicting_task["title"] = "Conflicting Update"
        conflicting_task["version"] = 0  # Old version
        
        response = client.post(
            "/api/tasks/task",
            json=conflicting_task,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data
        assert "conflict" in data["detail"]["message"].lower()
    
    def test_list_tasks(self, client, auth_headers, sample_task, test_user):
        """Test listing tasks"""
        # Create multiple tasks
        for i in range(3):
            task = sample_task.copy()
            task["id"] = str(uuid.uuid4())
            task["title"] = f"Task {i}"
            client.post("/api/tasks/task", json=task, headers=auth_headers)
        
        # List tasks
        response = client.get(
            f"/api/tasks/tasks?user_id={test_user['user_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 3
    
    def test_get_task_by_id(self, client, auth_headers, sample_task):
        """Test getting a single task by ID"""
        # Create task
        client.post("/api/tasks/task", json=sample_task, headers=auth_headers)
        
        # Get task
        response = client.get(
            f"/api/tasks/task/{sample_task['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_task["id"]
        assert data["title"] == sample_task["title"]
    
    def test_delete_task_soft(self, client, auth_headers, sample_task):
        """Test soft deleting a task"""
        # Create task
        client.post("/api/tasks/task", json=sample_task, headers=auth_headers)
        
        # Soft delete
        response = client.delete(
            f"/api/tasks/task/{sample_task['id']}?soft=true",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_task["id"]
        assert data["deleted_at"] is not None
        
        # Verify task is marked as deleted
        get_response = client.get(
            f"/api/tasks/task/{sample_task['id']}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["deleted_at"] is not None
    
    def test_unauthorized_access(self, client, sample_task):
        """Test accessing endpoints without authentication"""
        response = client.post("/api/tasks/task", json=sample_task)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTagCRUD:
    """Test Tag CRUD operations"""
    
    def test_create_tag(self, client, auth_headers, sample_tag):
        """Test creating a new tag"""
        response = client.post(
            "/api/tasks/tag",
            json=sample_tag,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_tag["id"]
        assert data["name"] == sample_tag["name"]
        assert data["color"] == sample_tag["color"]
    
    def test_list_tags(self, client, auth_headers, sample_tag, test_user):
        """Test listing tags"""
        # Create tags
        for i in range(2):
            tag = sample_tag.copy()
            tag["id"] = str(uuid.uuid4())
            tag["name"] = f"Tag {i}"
            client.post("/api/tasks/tag", json=tag, headers=auth_headers)
        
        # List tags
        response = client.get(
            f"/api/tasks/tags?user_id={test_user['user_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
    
    def test_delete_tag(self, client, auth_headers, sample_tag):
        """Test deleting a tag"""
        # Create tag
        client.post("/api/tasks/tag", json=sample_tag, headers=auth_headers)
        
        # Delete tag
        response = client.delete(
            f"/api/tasks/tag/{sample_tag['id']}?soft=true",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK


class TestBulkSync:
    """Test bulk synchronization"""
    
    def test_bulk_sync_tasks(self, client, auth_headers, sample_task, test_user):
        """Test bulk syncing multiple tasks"""
        tasks = []
        for i in range(5):
            task = sample_task.copy()
            task["id"] = str(uuid.uuid4())
            task["title"] = f"Bulk Task {i}"
            tasks.append(task)
        
        bulk_request = {
            "user_id": test_user["user_id"],
            "tasks": tasks,
            "tags": [],
            "kanban_items": []
        }
        
        response = client.post(
            "/api/tasks/bulk-sync",
            json=bulk_request,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 5
        assert data["conflict_count"] == 0
        assert data["error_count"] == 0
        assert len(data["results"]) == 5
    
    def test_bulk_sync_with_conflicts(self, client, auth_headers, sample_task, test_user):
        """Test bulk sync with version conflicts"""
        # Create task with version 1
        client.post("/api/tasks/task", json=sample_task, headers=auth_headers)
        
        # Try to sync with old version
        conflicting_task = sample_task.copy()
        conflicting_task["version"] = 0
        conflicting_task["title"] = "Conflicting Title"
        
        bulk_request = {
            "user_id": test_user["user_id"],
            "tasks": [conflicting_task],
            "tags": [],
            "kanban_items": []
        }
        
        response = client.post(
            "/api/tasks/bulk-sync",
            json=bulk_request,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conflict_count"] == 1
        assert data["results"][0]["status"] == "conflict"
    
    def test_bulk_sync_mixed_entities(self, client, auth_headers, sample_task, sample_tag, sample_kanban_item, test_user):
        """Test bulk sync with tasks, tags, and kanban items"""
        bulk_request = {
            "user_id": test_user["user_id"],
            "tasks": [sample_task],
            "tags": [sample_tag],
            "kanban_items": [sample_kanban_item]
        }
        
        response = client.post(
            "/api/tasks/bulk-sync",
            json=bulk_request,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3


class TestKanbanEndpoints:
    """Test Kanban endpoints"""
    
    def test_create_kanban_item(self, client, auth_headers, sample_kanban_item):
        """Test creating a Kanban item"""
        response = client.post(
            "/api/tasks/kanban/item",
            json=sample_kanban_item,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == sample_kanban_item["task_id"]
        assert data["column_type"] == "todo"
    
    def test_list_kanban_items(self, client, auth_headers, sample_kanban_item, test_user):
        """Test listing Kanban items"""
        # Create items
        for i in range(3):
            item = sample_kanban_item.copy()
            item["id"] = str(uuid.uuid4())
            item["position"] = i
            client.post("/api/tasks/kanban/item", json=item, headers=auth_headers)
        
        # List items
        response = client.get(
            f"/api/tasks/kanban/items?user_id={test_user['user_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 3


class TestStatsEndpoint:
    """Test statistics endpoint"""
    
    def test_get_sync_stats(self, client, auth_headers, sample_task, test_user):
        """Test getting sync statistics"""
        # Create some tasks
        client.post("/api/tasks/task", json=sample_task, headers=auth_headers)
        
        # Get stats
        response = client.get(
            f"/api/tasks/stats?user_id={test_user['user_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == test_user["user_id"]
        assert data["total_tasks"] >= 0
        assert "last_sync" in data


class TestCustomLists:
    """Test Custom Lists endpoints"""
    
    def test_create_custom_list(self, client, auth_headers, sample_custom_list):
        """Test creating a custom list"""
        response = client.post(
            "/api/tasks/custom-list",
            json=sample_custom_list,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == sample_custom_list["name"]
        assert data["values"] == sample_custom_list["values"]
    
    def test_list_custom_lists(self, client, auth_headers, sample_custom_list, test_user):
        """Test listing custom lists"""
        # Create list
        client.post("/api/tasks/custom-list", json=sample_custom_list, headers=auth_headers)
        
        # List
        response = client.get(
            f"/api/tasks/custom-lists?user_id={test_user['user_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] >= 1
