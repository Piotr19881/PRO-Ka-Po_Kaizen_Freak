"""
Script do wykonania migracji: Usunięcie starych schematów i utworzenie s06_tasks
"""
import psycopg2
from psycopg2 import sql
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.config import settings

def run_migration():
    """Wykonaj migrację bazy danych"""
    
    print("=" * 80)
    print("MIGRACJA: Usunięcie s02_tasks, s03_kanban → Utworzenie s06_tasks")
    print("=" * 80)
    
    try:
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD
        )
        conn.autocommit = False  # Transakcja
        cursor = conn.cursor()
        
        print("\n✅ Połączono z bazą danych")
        
        # KROK 1: Sprawdź czy schematy są puste
        print("\n" + "=" * 80)
        print("KROK 1: Weryfikacja - sprawdzanie czy schematy są puste")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM s02_tasks.tasks) as s02_count,
                (SELECT COUNT(*) FROM s03_kanban.cards) as s03_count
        """)
        
        s02_count, s03_count = cursor.fetchone()
        
        print(f"\n  s02_tasks.tasks: {s02_count} wierszy")
        print(f"  s03_kanban.cards: {s03_count} wierszy")
        
        if s02_count > 0 or s03_count > 0:
            print("\n❌ BŁĄD: Schematy nie są puste!")
            print("   Przed migracją należy wyeksportować dane lub je usunąć.")
            return 1
        
        print("\n✅ Schematy są puste - można bezpiecznie usunąć")
        
        # KROK 2: Usuń stare schematy
        print("\n" + "=" * 80)
        print("KROK 2: Usuwanie starych schematów")
        print("=" * 80)
        
        print("\n  🗑️  Usuwanie s02_tasks...")
        cursor.execute("DROP SCHEMA IF EXISTS s02_tasks CASCADE")
        print("  ✅ s02_tasks usunięty")
        
        print("\n  🗑️  Usuwanie s03_kanban...")
        cursor.execute("DROP SCHEMA IF EXISTS s03_kanban CASCADE")
        print("  ✅ s03_kanban usunięty")
        
        # KROK 3: Utwórz nowy schemat
        print("\n" + "=" * 80)
        print("KROK 3: Tworzenie nowego schematu s06_tasks")
        print("=" * 80)
        
        print("\n  📦 Tworzenie schematu s06_tasks...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS s06_tasks")
        print("  ✅ Schemat utworzony")
        
        # KROK 4: Utwórz trigger function
        print("\n  🔧 Tworzenie trigger function...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION s06_tasks.update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("  ✅ Trigger function utworzony")
        
        # KROK 5: Utwórz tabele
        print("\n" + "=" * 80)
        print("KROK 4: Tworzenie tabel")
        print("=" * 80)
        
        # Tabela: tasks
        print("\n  📋 Tworzenie tabeli tasks...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                parent_id TEXT REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
                
                title TEXT NOT NULL CHECK (length(title) >= 1 AND length(title) <= 500),
                description TEXT,
                status BOOLEAN DEFAULT FALSE,
                
                due_date TIMESTAMP,
                completion_date TIMESTAMP,
                alarm_date TIMESTAMP,
                
                note_id INTEGER,
                custom_data JSONB DEFAULT '{}',
                archived BOOLEAN DEFAULT FALSE,
                "order" INTEGER DEFAULT 0,
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1,
                
                CONSTRAINT valid_parent CHECK (parent_id IS NULL OR parent_id != id)
            )
        """)
        
        # Indexes dla tasks
        cursor.execute("CREATE INDEX idx_tasks_user ON s06_tasks.tasks(user_id) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_tasks_parent ON s06_tasks.tasks(parent_id) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_tasks_status ON s06_tasks.tasks(user_id, status) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_tasks_updated ON s06_tasks.tasks(updated_at DESC)")
        cursor.execute("CREATE INDEX idx_tasks_deleted ON s06_tasks.tasks(deleted_at) WHERE deleted_at IS NOT NULL")
        
        # Trigger
        cursor.execute("""
            CREATE TRIGGER update_tasks_updated_at
                BEFORE UPDATE ON s06_tasks.tasks
                FOR EACH ROW
                EXECUTE FUNCTION s06_tasks.update_updated_at_column()
        """)
        print("  ✅ Tabela tasks + indexes + trigger")
        
        # Tabela: task_tags
        print("\n  📋 Tworzenie tabeli task_tags...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.task_tags (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
                color TEXT NOT NULL DEFAULT '#CCCCCC' CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Partial unique index zamiast constraint
        cursor.execute("CREATE UNIQUE INDEX idx_unique_user_tag_name ON s06_tasks.task_tags(user_id, name) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_task_tags_user ON s06_tasks.task_tags(user_id) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_task_tags_updated ON s06_tasks.task_tags(updated_at DESC)")
        cursor.execute("""
            CREATE TRIGGER update_task_tags_updated_at
                BEFORE UPDATE ON s06_tasks.task_tags
                FOR EACH ROW
                EXECUTE FUNCTION s06_tasks.update_updated_at_column()
        """)
        print("  ✅ Tabela task_tags")
        
        # Tabela: task_tag_assignments
        print("\n  📋 Tworzenie tabeli task_tag_assignments...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.task_tag_assignments (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
                tag_id TEXT NOT NULL REFERENCES s06_tasks.task_tags(id) ON DELETE CASCADE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_task_tag UNIQUE (task_id, tag_id)
            )
        """)
        
        cursor.execute("CREATE INDEX idx_task_tag_assign_task ON s06_tasks.task_tag_assignments(task_id)")
        cursor.execute("CREATE INDEX idx_task_tag_assign_tag ON s06_tasks.task_tag_assignments(tag_id)")
        print("  ✅ Tabela task_tag_assignments")
        
        # Tabela: task_custom_lists
        print("\n  📋 Tworzenie tabeli task_custom_lists...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.task_custom_lists (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
                values JSONB NOT NULL DEFAULT '[]',
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Partial unique index
        cursor.execute("CREATE UNIQUE INDEX idx_unique_user_list_name ON s06_tasks.task_custom_lists(user_id, name) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_custom_lists_user ON s06_tasks.task_custom_lists(user_id) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_custom_lists_updated ON s06_tasks.task_custom_lists(updated_at DESC)")
        cursor.execute("""
            CREATE TRIGGER update_task_custom_lists_updated_at
                BEFORE UPDATE ON s06_tasks.task_custom_lists
                FOR EACH ROW
                EXECUTE FUNCTION s06_tasks.update_updated_at_column()
        """)
        print("  ✅ Tabela task_custom_lists")
        
        # Tabela: kanban_items
        print("\n  📋 Tworzenie tabeli kanban_items...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.kanban_items (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                task_id TEXT NOT NULL REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
                column_type TEXT NOT NULL CHECK (column_type IN ('todo', 'in_progress', 'done', 'on_hold', 'review')),
                position INTEGER NOT NULL DEFAULT 0,
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Partial unique index
        cursor.execute("CREATE UNIQUE INDEX idx_unique_user_task_kanban ON s06_tasks.kanban_items(user_id, task_id) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_kanban_items_user ON s06_tasks.kanban_items(user_id) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_kanban_items_column ON s06_tasks.kanban_items(user_id, column_type, position) WHERE deleted_at IS NULL")
        cursor.execute("CREATE INDEX idx_kanban_items_updated ON s06_tasks.kanban_items(updated_at DESC)")
        cursor.execute("""
            CREATE TRIGGER update_kanban_items_updated_at
                BEFORE UPDATE ON s06_tasks.kanban_items
                FOR EACH ROW
                EXECUTE FUNCTION s06_tasks.update_updated_at_column()
        """)
        print("  ✅ Tabela kanban_items")
        
        # Tabela: kanban_settings
        print("\n  📋 Tworzenie tabeli kanban_settings...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.kanban_settings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                settings JSONB NOT NULL DEFAULT '{}',
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Unique index
        cursor.execute("CREATE UNIQUE INDEX idx_unique_user_kanban_settings ON s06_tasks.kanban_settings(user_id)")
        cursor.execute("CREATE INDEX idx_kanban_settings_user ON s06_tasks.kanban_settings(user_id)")
        cursor.execute("CREATE INDEX idx_kanban_settings_updated ON s06_tasks.kanban_settings(updated_at DESC)")
        cursor.execute("""
            CREATE TRIGGER update_kanban_settings_updated_at
                BEFORE UPDATE ON s06_tasks.kanban_settings
                FOR EACH ROW
                EXECUTE FUNCTION s06_tasks.update_updated_at_column()
        """)
        print("  ✅ Tabela kanban_settings")
        
        # Tabela: task_history
        print("\n  📋 Tworzenie tabeli task_history...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.task_history (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                task_id TEXT NOT NULL REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
                action_type TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                details JSONB DEFAULT '{}',
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        cursor.execute("CREATE INDEX idx_task_history_task ON s06_tasks.task_history(task_id, created_at DESC)")
        cursor.execute("CREATE INDEX idx_task_history_user ON s06_tasks.task_history(user_id, created_at DESC)")
        cursor.execute("CREATE INDEX idx_task_history_created ON s06_tasks.task_history(created_at DESC)")
        print("  ✅ Tabela task_history")
        
        # Tabela: columns_config
        print("\n  📋 Tworzenie tabeli columns_config...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s06_tasks.columns_config (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
                columns JSONB NOT NULL DEFAULT '[]',
                
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        # Unique index
        cursor.execute("CREATE UNIQUE INDEX idx_unique_user_columns_config ON s06_tasks.columns_config(user_id)")
        cursor.execute("CREATE INDEX idx_columns_config_user ON s06_tasks.columns_config(user_id)")
        cursor.execute("CREATE INDEX idx_columns_config_updated ON s06_tasks.columns_config(updated_at DESC)")
        cursor.execute("""
            CREATE TRIGGER update_columns_config_updated_at
                BEFORE UPDATE ON s06_tasks.columns_config
                FOR EACH ROW
                EXECUTE FUNCTION s06_tasks.update_updated_at_column()
        """)
        print("  ✅ Tabela columns_config")
        
        # COMMIT
        conn.commit()
        
        print("\n" + "=" * 80)
        print("WERYFIKACJA")
        print("=" * 80)
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 's06_tasks' 
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"\n✅ Utworzono {len(tables)} tabel w s06_tasks:\n")
        for table in tables:
            print(f"  • {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ MIGRACJA ZAKOŃCZONA SUKCESEM")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        
        if conn:
            conn.rollback()
            print("\n🔄 Rollback wykonany")
        
        return 1


if __name__ == "__main__":
    print("\n⚠️  UWAGA: Ta operacja usunie schematy s02_tasks i s03_kanban!")
    print("           Sprawdzono że są puste, ale warto mieć backup.\n")
    
    response = input("Czy kontynuować? (tak/nie): ")
    
    if response.lower() in ['tak', 'yes', 'y', 't']:
        exit_code = run_migration()
        sys.exit(exit_code)
    else:
        print("\n❌ Anulowano")
        sys.exit(0)
