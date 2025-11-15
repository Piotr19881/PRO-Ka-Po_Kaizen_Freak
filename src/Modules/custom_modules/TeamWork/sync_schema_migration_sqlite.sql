-- ============================================================================
-- MIGRACJA SCHEMATU - DODANIE METADANYCH SYNCHRONIZACJI (SQLite)
-- ============================================================================
-- Task 5.1: Rozszerzenie istniejących tabel o kolumny sync
-- UWAGA: Wersja dla lokalnej bazy SQLite w aplikacji
-- ============================================================================

-- Dodaj kolumny sync do work_groups
ALTER TABLE work_groups ADD COLUMN server_id INTEGER; -- ID z serwera API
ALTER TABLE work_groups ADD COLUMN last_synced DATETIME;
ALTER TABLE work_groups ADD COLUMN sync_status TEXT DEFAULT 'pending'; -- pending, synced, conflict, error
ALTER TABLE work_groups ADD COLUMN version INTEGER DEFAULT 1; -- dla conflict resolution
ALTER TABLE work_groups ADD COLUMN modified_locally BOOLEAN DEFAULT 0;

-- Dodaj kolumny sync do topics
ALTER TABLE topics ADD COLUMN server_id INTEGER;
ALTER TABLE topics ADD COLUMN last_synced DATETIME;
ALTER TABLE topics ADD COLUMN sync_status TEXT DEFAULT 'pending';
ALTER TABLE topics ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE topics ADD COLUMN modified_locally BOOLEAN DEFAULT 0;

-- Dodaj kolumny sync do messages
ALTER TABLE messages ADD COLUMN server_id INTEGER;
ALTER TABLE messages ADD COLUMN last_synced DATETIME;
ALTER TABLE messages ADD COLUMN sync_status TEXT DEFAULT 'pending';
ALTER TABLE messages ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE messages ADD COLUMN modified_locally BOOLEAN DEFAULT 0;

-- Dodaj kolumny sync do tasks
ALTER TABLE tasks ADD COLUMN server_id INTEGER;
ALTER TABLE tasks ADD COLUMN last_synced DATETIME;
ALTER TABLE tasks ADD COLUMN sync_status TEXT DEFAULT 'pending';
ALTER TABLE tasks ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE tasks ADD COLUMN modified_locally BOOLEAN DEFAULT 0;

-- Dodaj kolumny sync do topic_files
ALTER TABLE topic_files ADD COLUMN server_id INTEGER;
ALTER TABLE topic_files ADD COLUMN last_synced DATETIME;
ALTER TABLE topic_files ADD COLUMN sync_status TEXT DEFAULT 'pending';
ALTER TABLE topic_files ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE topic_files ADD COLUMN modified_locally BOOLEAN DEFAULT 0;

-- Tabela metadanych synchronizacji globalnej
CREATE TABLE IF NOT EXISTS sync_metadata (
    sync_meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL, -- groups, topics, messages, tasks, files
    last_pull_timestamp DATETIME,
    last_push_timestamp DATETIME,
    last_full_sync DATETIME,
    sync_errors_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    UNIQUE(entity_type)
);

-- Tabela konfliktów
CREATE TABLE IF NOT EXISTS sync_conflicts (
    conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_local_id INTEGER NOT NULL,
    entity_server_id INTEGER,
    local_version INTEGER,
    server_version INTEGER,
    local_data TEXT, -- JSON z danymi lokalnymi
    server_data TEXT, -- JSON z danymi z serwera
    conflict_detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    resolution_strategy TEXT, -- keep_local, keep_remote, merge, manual
    resolved_by INTEGER,
    FOREIGN KEY (resolved_by) REFERENCES users(user_id)
);

-- Indeksy dla wydajności synchronizacji
CREATE INDEX IF NOT EXISTS idx_groups_sync ON work_groups(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_groups_server ON work_groups(server_id);
CREATE INDEX IF NOT EXISTS idx_topics_sync ON topics(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_topics_server ON topics(server_id);
CREATE INDEX IF NOT EXISTS idx_messages_sync ON messages(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_messages_server ON messages(server_id);
CREATE INDEX IF NOT EXISTS idx_tasks_sync ON tasks(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_tasks_server ON tasks(server_id);
CREATE INDEX IF NOT EXISTS idx_files_sync ON topic_files(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_files_server ON topic_files(server_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON sync_conflicts(entity_type, resolved_at);

-- Triggery do automatycznego oznaczania modified_locally (SQLite)

-- Trigger dla work_groups
CREATE TRIGGER IF NOT EXISTS trg_groups_modified
AFTER UPDATE ON work_groups
FOR EACH ROW
WHEN (OLD.group_name != NEW.group_name 
      OR OLD.description != NEW.description
      OR OLD.is_active != NEW.is_active)
BEGIN
    UPDATE work_groups 
    SET modified_locally = 1, 
        sync_status = 'pending'
    WHERE group_id = NEW.group_id;
END;

-- Trigger dla topics
CREATE TRIGGER IF NOT EXISTS trg_topics_modified
AFTER UPDATE ON topics
FOR EACH ROW
WHEN (OLD.topic_name != NEW.topic_name 
      OR OLD.is_active != NEW.is_active)
BEGIN
    UPDATE topics 
    SET modified_locally = 1, 
        sync_status = 'pending'
    WHERE topic_id = NEW.topic_id;
END;

-- Trigger dla messages
CREATE TRIGGER IF NOT EXISTS trg_messages_modified
AFTER UPDATE ON messages
FOR EACH ROW
WHEN (OLD.content != NEW.content 
      OR OLD.background_color != NEW.background_color
      OR OLD.is_important != NEW.is_important)
BEGIN
    UPDATE messages 
    SET modified_locally = 1, 
        sync_status = 'pending'
    WHERE message_id = NEW.message_id;
END;

-- Trigger dla tasks
CREATE TRIGGER IF NOT EXISTS trg_tasks_modified
AFTER UPDATE ON tasks
FOR EACH ROW
WHEN (OLD.task_subject != NEW.task_subject
      OR OLD.task_description != NEW.task_description
      OR OLD.assigned_to != NEW.assigned_to
      OR OLD.due_date != NEW.due_date
      OR OLD.completed != NEW.completed
      OR OLD.is_important != NEW.is_important)
BEGIN
    UPDATE tasks 
    SET modified_locally = 1, 
        sync_status = 'pending'
    WHERE task_id = NEW.task_id;
END;

-- Trigger dla topic_files
CREATE TRIGGER IF NOT EXISTS trg_files_modified
AFTER UPDATE ON topic_files
FOR EACH ROW
WHEN (OLD.is_important != NEW.is_important)
BEGIN
    UPDATE topic_files 
    SET modified_locally = 1, 
        sync_status = 'pending'
    WHERE file_id = NEW.file_id;
END;

-- Inicjalizacja sync_metadata dla wszystkich typów encji
INSERT OR IGNORE INTO sync_metadata (entity_type) VALUES ('groups');
INSERT OR IGNORE INTO sync_metadata (entity_type) VALUES ('topics');
INSERT OR IGNORE INTO sync_metadata (entity_type) VALUES ('messages');
INSERT OR IGNORE INTO sync_metadata (entity_type) VALUES ('tasks');
INSERT OR IGNORE INTO sync_metadata (entity_type) VALUES ('files');
