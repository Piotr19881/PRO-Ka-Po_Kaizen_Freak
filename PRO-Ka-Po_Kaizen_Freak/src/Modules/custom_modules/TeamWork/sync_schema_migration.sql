-- ============================================================================
-- MIGRACJA SCHEMATU - DODANIE METADANYCH SYNCHRONIZACJI (PostgreSQL)
-- ============================================================================
-- Task 5.1: Rozszerzenie istniejących tabel o kolumny sync
-- UWAGA: Wersja dla bazy PostgreSQL na Render (schema: s02_teamwork)
-- ============================================================================

-- Ustaw schemat roboczy
SET search_path TO s02_teamwork;

-- Dodaj kolumny sync do work_groups
ALTER TABLE s02_teamwork.work_groups ADD COLUMN IF NOT EXISTS server_id INTEGER; -- ID z serwera API
ALTER TABLE s02_teamwork.work_groups ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP;
ALTER TABLE s02_teamwork.work_groups ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending'; -- pending, synced, conflict, error
ALTER TABLE s02_teamwork.work_groups ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1; -- dla conflict resolution
ALTER TABLE s02_teamwork.work_groups ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- Dodaj kolumny sync do topics
ALTER TABLE s02_teamwork.topics ADD COLUMN IF NOT EXISTS server_id INTEGER;
ALTER TABLE s02_teamwork.topics ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP;
ALTER TABLE s02_teamwork.topics ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE s02_teamwork.topics ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE s02_teamwork.topics ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- Dodaj kolumny sync do messages
ALTER TABLE s02_teamwork.messages ADD COLUMN IF NOT EXISTS server_id INTEGER;
ALTER TABLE s02_teamwork.messages ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP;
ALTER TABLE s02_teamwork.messages ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE s02_teamwork.messages ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE s02_teamwork.messages ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- Dodaj kolumny sync do tasks
ALTER TABLE s02_teamwork.tasks ADD COLUMN IF NOT EXISTS server_id INTEGER;
ALTER TABLE s02_teamwork.tasks ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP;
ALTER TABLE s02_teamwork.tasks ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE s02_teamwork.tasks ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE s02_teamwork.tasks ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- Dodaj kolumny sync do topic_files
ALTER TABLE s02_teamwork.topic_files ADD COLUMN IF NOT EXISTS server_id INTEGER;
ALTER TABLE s02_teamwork.topic_files ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP;
ALTER TABLE s02_teamwork.topic_files ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE s02_teamwork.topic_files ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE s02_teamwork.topic_files ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- Tabela metadanych synchronizacji globalnej
CREATE TABLE IF NOT EXISTS sync_metadata (
    sync_meta_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- groups, topics, messages, tasks, files
    last_pull_timestamp TIMESTAMP,
    last_push_timestamp TIMESTAMP,
    last_full_sync TIMESTAMP,
    sync_errors_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    UNIQUE(entity_type)
);

-- Tabela konfliktów
CREATE TABLE IF NOT EXISTS sync_conflicts (
    conflict_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_local_id INTEGER NOT NULL,
    entity_server_id INTEGER,
    local_version INTEGER,
    server_version INTEGER,
    local_data TEXT, -- JSON z danymi lokalnymi
    server_data TEXT, -- JSON z danymi z serwera
    conflict_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_strategy VARCHAR(20), -- keep_local, keep_remote, merge, manual
    resolved_by INTEGER,
    FOREIGN KEY (resolved_by) REFERENCES users(user_id)
);

-- Indeksy dla wydajności synchronizacji
CREATE INDEX IF NOT EXISTS idx_groups_sync ON s02_teamwork.work_groups(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_groups_server ON s02_teamwork.work_groups(server_id);
CREATE INDEX IF NOT EXISTS idx_topics_sync ON s02_teamwork.topics(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_topics_server ON s02_teamwork.topics(server_id);
CREATE INDEX IF NOT EXISTS idx_messages_sync ON s02_teamwork.messages(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_messages_server ON s02_teamwork.messages(server_id);
CREATE INDEX IF NOT EXISTS idx_tasks_sync ON s02_teamwork.tasks(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_tasks_server ON s02_teamwork.tasks(server_id);
CREATE INDEX IF NOT EXISTS idx_files_sync ON s02_teamwork.topic_files(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_files_server ON s02_teamwork.topic_files(server_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON s02_teamwork.sync_conflicts(entity_type, resolved_at);

-- Triggery do automatycznego oznaczania modified_locally (PostgreSQL)

-- Funkcja trigger dla work_groups
CREATE OR REPLACE FUNCTION trg_groups_modified_func()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.group_name IS DISTINCT FROM NEW.group_name 
       OR OLD.description IS DISTINCT FROM NEW.description
       OR OLD.is_active IS DISTINCT FROM NEW.is_active THEN
        NEW.modified_locally = TRUE;
        NEW.sync_status = 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_groups_modified ON s02_teamwork.work_groups;
CREATE TRIGGER trg_groups_modified
BEFORE UPDATE ON s02_teamwork.work_groups
FOR EACH ROW
EXECUTE FUNCTION trg_groups_modified_func();

-- Funkcja trigger dla topics
CREATE OR REPLACE FUNCTION trg_topics_modified_func()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.topic_name IS DISTINCT FROM NEW.topic_name 
       OR OLD.is_active IS DISTINCT FROM NEW.is_active THEN
        NEW.modified_locally = TRUE;
        NEW.sync_status = 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_topics_modified ON s02_teamwork.topics;
CREATE TRIGGER trg_topics_modified
BEFORE UPDATE ON s02_teamwork.topics
FOR EACH ROW
EXECUTE FUNCTION trg_topics_modified_func();

-- Funkcja trigger dla messages
CREATE OR REPLACE FUNCTION trg_messages_modified_func()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.content IS DISTINCT FROM NEW.content 
       OR OLD.background_color IS DISTINCT FROM NEW.background_color
       OR OLD.is_important IS DISTINCT FROM NEW.is_important THEN
        NEW.modified_locally = TRUE;
        NEW.sync_status = 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_messages_modified ON s02_teamwork.messages;
CREATE TRIGGER trg_messages_modified
BEFORE UPDATE ON s02_teamwork.messages
FOR EACH ROW
EXECUTE FUNCTION trg_messages_modified_func();

-- Funkcja trigger dla tasks
CREATE OR REPLACE FUNCTION trg_tasks_modified_func()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.task_subject IS DISTINCT FROM NEW.task_subject
       OR OLD.task_description IS DISTINCT FROM NEW.task_description
       OR OLD.assigned_to IS DISTINCT FROM NEW.assigned_to
       OR OLD.due_date IS DISTINCT FROM NEW.due_date
       OR OLD.completed IS DISTINCT FROM NEW.completed
       OR OLD.is_important IS DISTINCT FROM NEW.is_important THEN
        NEW.modified_locally = TRUE;
        NEW.sync_status = 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tasks_modified ON s02_teamwork.tasks;
CREATE TRIGGER trg_tasks_modified
BEFORE UPDATE ON s02_teamwork.tasks
FOR EACH ROW
EXECUTE FUNCTION trg_tasks_modified_func();

-- Funkcja trigger dla topic_files
CREATE OR REPLACE FUNCTION trg_files_modified_func()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_important IS DISTINCT FROM NEW.is_important THEN
        NEW.modified_locally = TRUE;
        NEW.sync_status = 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_files_modified ON s02_teamwork.topic_files;
CREATE TRIGGER trg_files_modified
BEFORE UPDATE ON s02_teamwork.topic_files
FOR EACH ROW
EXECUTE FUNCTION trg_files_modified_func();

-- Inicjalizacja sync_metadata dla wszystkich typów encji
INSERT INTO sync_metadata (entity_type) VALUES ('groups')
ON CONFLICT (entity_type) DO NOTHING;
INSERT INTO sync_metadata (entity_type) VALUES ('topics')
ON CONFLICT (entity_type) DO NOTHING;
INSERT INTO sync_metadata (entity_type) VALUES ('messages')
ON CONFLICT (entity_type) DO NOTHING;
INSERT INTO sync_metadata (entity_type) VALUES ('tasks')
ON CONFLICT (entity_type) DO NOTHING;
INSERT INTO sync_metadata (entity_type) VALUES ('files')
ON CONFLICT (entity_type) DO NOTHING;
