"""
Test importu i walidacji modeli Tasks
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_models_import():
    """Test importu SQLAlchemy models"""
    print("=" * 80)
    print("TEST 1: Import SQLAlchemy Models")
    print("=" * 80)
    
    try:
        from app.tasks_models import (
            Task, TaskTag, TaskTagAssignment, TaskCustomList,
            KanbanItem, KanbanSettings, TaskHistory, ColumnsConfig
        )
        
        print("\n✅ Wszystkie modele SQLAlchemy zaimportowane:")
        models = [Task, TaskTag, TaskTagAssignment, TaskCustomList, 
                  KanbanItem, KanbanSettings, TaskHistory, ColumnsConfig]
        
        for model in models:
            print(f"  • {model.__name__} (tabela: {model.__tablename__})")
        
        # Sprawdź atrybuty modelu Task
        print("\n📋 Kolumny modelu Task:")
        for col_name, col in Task.__table__.columns.items():
            col_type = str(col.type)
            nullable = "NULL" if col.nullable else "NOT NULL"
            print(f"  • {col_name}: {col_type} {nullable}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ BŁĄD importu models: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schemas_import():
    """Test importu Pydantic schemas"""
    print("\n" + "=" * 80)
    print("TEST 2: Import Pydantic Schemas")
    print("=" * 80)
    
    try:
        from app.tasks_schemas import (
            TaskBase, TaskCreate, TaskResponse,
            TaskTagBase, TaskTagCreate, TaskTagResponse,
            KanbanItemBase, KanbanItemCreate, KanbanItemResponse,
            BulkSyncRequest, BulkSyncResponse,
            ConflictErrorResponse, DeleteResponse
        )
        
        print("\n✅ Wszystkie schematy Pydantic zaimportowane:")
        schemas = [
            TaskBase, TaskCreate, TaskResponse,
            TaskTagBase, TaskTagCreate, TaskTagResponse,
            KanbanItemBase, KanbanItemCreate, KanbanItemResponse,
            BulkSyncRequest, BulkSyncResponse,
            ConflictErrorResponse, DeleteResponse
        ]
        
        for schema in schemas:
            print(f"  • {schema.__name__}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ BŁĄD importu schemas: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_validation():
    """Test walidacji Pydantic schema"""
    print("\n" + "=" * 80)
    print("TEST 3: Walidacja Pydantic Schema")
    print("=" * 80)
    
    try:
        from app.tasks_schemas import TaskBase, TaskTagBase
        
        # Test 1: Poprawne dane
        print("\n✅ Test 1: Poprawne dane dla TaskBase")
        task = TaskBase(
            id="test-123",
            title="Test Task",
            description="Test description",
            status=False,
            version=1
        )
        print(f"  • Utworzono: {task.title} (id={task.id}, status={task.status})")
        
        # Test 2: Walidacja title
        print("\n✅ Test 2: Walidacja title (nie może być pusty)")
        try:
            invalid_task = TaskBase(
                id="test-456",
                title="   ",  # Pusty po strip()
                version=1
            )
            print("  ❌ Nie złapano błędu walidacji!")
            return False
        except ValueError as e:
            print(f"  • Poprawnie złapano błąd: {e}")
        
        # Test 3: Walidacja koloru tagu
        print("\n✅ Test 3: Walidacja koloru HEX dla TaskTagBase")
        tag = TaskTagBase(
            id="tag-1",
            name="Important",
            color="#FF0000",  # Poprawny HEX
            version=1
        )
        print(f"  • Utworzono tag: {tag.name} ({tag.color})")
        
        # Test 4: Niepoprawny kolor
        print("\n✅ Test 4: Niepoprawny kolor HEX")
        try:
            invalid_tag = TaskTagBase(
                id="tag-2",
                name="Test",
                color="red",  # Niepoprawny format
                version=1
            )
            print("  ❌ Nie złapano błędu walidacji koloru!")
            return False
        except ValueError as e:
            print(f"  • Poprawnie złapano błąd: {e}")
        
        print("\n✅ Wszystkie testy walidacji przeszły")
        return True
        
    except Exception as e:
        print(f"\n❌ BŁĄD testu walidacji: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connection():
    """Test połączenia z bazą danych"""
    print("\n" + "=" * 80)
    print("TEST 4: Połączenie z bazą danych")
    print("=" * 80)
    
    try:
        from app.database import test_connection
        from app.config import settings
        
        print(f"\nHost: {settings.DATABASE_HOST}")
        print(f"Database: {settings.DATABASE_NAME}")
        print(f"Schema: s06_tasks")
        
        if test_connection():
            print("\n✅ Połączenie z bazą działa")
            return True
        else:
            print("\n❌ Brak połączenia z bazą")
            return False
            
    except Exception as e:
        print(f"\n❌ BŁĄD testu połączenia: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TESTY MODELI I SCHEMATÓW TASKS")
    print("=" * 80)
    
    results = []
    
    # Test 1: Import models
    results.append(("Import SQLAlchemy Models", test_models_import()))
    
    # Test 2: Import schemas
    results.append(("Import Pydantic Schemas", test_schemas_import()))
    
    # Test 3: Walidacja
    results.append(("Walidacja Pydantic", test_schema_validation()))
    
    # Test 4: Połączenie z bazą
    results.append(("Połączenie z bazą", test_database_connection()))
    
    # Podsumowanie
    print("\n" + "=" * 80)
    print("PODSUMOWANIE TESTÓW")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ WSZYSTKIE TESTY PRZESZŁY")
        sys.exit(0)
    else:
        print("❌ NIEKTÓRE TESTY NIE POWIODŁY SIĘ")
        sys.exit(1)
