-- ============================================================================
-- MIGRACJA: Dodanie kolumn synchronizacji i tabel współpracy do s02_teamwork
-- ============================================================================
-- Data: 2024-11-14
-- Opis: Dodaje kolumny sync metadata do istniejących tabel + nowe tabele Phase 5 i 6
-- ============================================================================

SET search_path TO s02_teamwork;

-- ============================================================================
-- KROK 1: Dodaj kolumny synchronizacji do istniejących tabel
-- ============================================================================

-- work_groups
ALTER TABLE s02_teamwork.work_groups 
    ADD COLUMN IF NOT EXISTS server_id INTEGER,
    ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP,
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- topics
ALTER TABLE s02_teamwork.topics 
    ADD COLUMN IF NOT EXISTS server_id INTEGER,
    ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP,
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- messages
ALTER TABLE s02_teamwork.messages 
    ADD COLUMN IF NOT EXISTS server_id INTEGER,
    ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP,
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- tasks
ALTER TABLE s02_teamwork.tasks 
    ADD COLUMN IF NOT EXISTS server_id INTEGER,
    ADD COLUMN IF NOT EXISTS last_synced TIMESTAMP,
    ADD COLUMN IF NOT EXISTS sync_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
    ADD COLUMN IF NOT EXISTS modified_locally BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- KROK 2: Utwórz nowe tabele (Phase 5 & 6)
-- ============================================================================

-- Tabela plików (Phase 2 - B2 integration)
CREATE TABLE IF NOT EXISTS s02_teamwork.topic_files (
    file_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_size INTEGER,
    content_type VARCHAR(200),
    
    -- Backblaze B2 identifiers
    b2_file_id VARCHAR(200) NOT NULL,
    b2_file_name VARCHAR(1000) NOT NULL,
    download_url VARCHAR(2000) NOT NULL,
    
    -- Metadata
    uploaded_by TEXT NOT NULL REFERENCES s01_user_accounts.users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_important BOOLEAN DEFAULT FALSE,
    
    -- Sync metadata (Phase 5)
    server_id INTEGER,
    last_synced TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    modified_locally BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE s02_teamwork.topic_files IS 'Pliki załączone do wątków (przechowywane w Backblaze B2)';

-- Tabela członków wątków (Phase 6 - collaboration)
CREATE TABLE IF NOT EXISTS s02_teamwork.topic_members (
    topic_member_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(topic_id, user_id)
);

COMMENT ON TABLE s02_teamwork.topic_members IS 'Członkowie wątków z rozszerzonymi rolami (Phase 6)';

-- Tabela zaproszeń (Phase 6)
CREATE TABLE IF NOT EXISTS s02_teamwork.topic_invitations (
    invitation_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    invited_email VARCHAR(255) NOT NULL,
    invited_by TEXT NOT NULL REFERENCES s01_user_accounts.users(id),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'member', 'viewer')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    token VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(topic_id, invited_email)
);

COMMENT ON TABLE s02_teamwork.topic_invitations IS 'Zaproszenia do wątków tematycznych (Phase 6)';

-- Tabela linków udostępniania (Phase 6)
CREATE TABLE IF NOT EXISTS s02_teamwork.topic_share_links (
    share_link_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    created_by TEXT NOT NULL REFERENCES s01_user_accounts.users(id),
    token VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer' CHECK (role IN ('member', 'viewer')),
    max_uses INTEGER,
    current_uses INTEGER DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE s02_teamwork.topic_share_links IS 'Linki do udostępniania wątków (Phase 6)';

-- Tabela metadanych synchronizacji (Phase 5)
CREATE TABLE IF NOT EXISTS s02_teamwork.sync_metadata (
    sync_meta_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    last_pull_timestamp TIMESTAMP,
    last_push_timestamp TIMESTAMP,
    last_full_sync TIMESTAMP,
    sync_errors_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    
    UNIQUE(entity_type)
);

COMMENT ON TABLE s02_teamwork.sync_metadata IS 'Globalne metadane synchronizacji';

-- Tabela konfliktów synchronizacji (Phase 5)
CREATE TABLE IF NOT EXISTS s02_teamwork.sync_conflicts (
    conflict_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    entity_local_id INTEGER NOT NULL,
    entity_server_id INTEGER,
    local_version INTEGER,
    server_version INTEGER,
    local_data TEXT,
    server_data TEXT,
    conflict_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_strategy VARCHAR(20) CHECK (resolution_strategy IN ('keep_local', 'keep_remote', 'merge', 'manual')),
    resolved_by TEXT REFERENCES s01_user_accounts.users(id)
);

COMMENT ON TABLE s02_teamwork.sync_conflicts IS 'Rejestr konfliktów synchronizacji';

-- ============================================================================
-- KROK 3: Dodaj indeksy dla wydajności
-- ============================================================================

-- Indeksy synchronizacji dla istniejących tabel
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

-- Indeksy dla nowych tabel
CREATE INDEX IF NOT EXISTS idx_topic_members_user ON s02_teamwork.topic_members(user_id);
CREATE INDEX IF NOT EXISTS idx_topic_members_topic ON s02_teamwork.topic_members(topic_id);
CREATE INDEX IF NOT EXISTS idx_invitations_topic ON s02_teamwork.topic_invitations(topic_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON s02_teamwork.topic_invitations(invited_email);
CREATE INDEX IF NOT EXISTS idx_invitations_status ON s02_teamwork.topic_invitations(status);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON s02_teamwork.topic_invitations(token);
CREATE INDEX IF NOT EXISTS idx_share_links_topic ON s02_teamwork.topic_share_links(topic_id);
CREATE INDEX IF NOT EXISTS idx_share_links_token ON s02_teamwork.topic_share_links(token);
CREATE INDEX IF NOT EXISTS idx_share_links_active ON s02_teamwork.topic_share_links(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON s02_teamwork.sync_conflicts(entity_type, resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_conflicts_entity ON s02_teamwork.sync_conflicts(entity_type, entity_server_id);

-- ============================================================================
-- KROK 4: Utwórz triggery dla automatycznego oznaczania zmian
-- ============================================================================

-- Funkcja trigger dla work_groups
CREATE OR REPLACE FUNCTION s02_teamwork.trg_groups_modified_func()
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
EXECUTE FUNCTION s02_teamwork.trg_groups_modified_func();

-- Funkcja trigger dla topics
CREATE OR REPLACE FUNCTION s02_teamwork.trg_topics_modified_func()
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
EXECUTE FUNCTION s02_teamwork.trg_topics_modified_func();

-- Funkcja trigger dla messages
CREATE OR REPLACE FUNCTION s02_teamwork.trg_messages_modified_func()
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
EXECUTE FUNCTION s02_teamwork.trg_messages_modified_func();

-- Funkcja trigger dla tasks
CREATE OR REPLACE FUNCTION s02_teamwork.trg_tasks_modified_func()
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
EXECUTE FUNCTION s02_teamwork.trg_tasks_modified_func();

-- Funkcja trigger dla topic_files
CREATE OR REPLACE FUNCTION s02_teamwork.trg_files_modified_func()
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
EXECUTE FUNCTION s02_teamwork.trg_files_modified_func();

-- ============================================================================
-- KROK 5: Inicjalizacja metadanych synchronizacji
-- ============================================================================

INSERT INTO s02_teamwork.sync_metadata (entity_type) VALUES ('groups')
ON CONFLICT (entity_type) DO NOTHING;

INSERT INTO s02_teamwork.sync_metadata (entity_type) VALUES ('topics')
ON CONFLICT (entity_type) DO NOTHING;

INSERT INTO s02_teamwork.sync_metadata (entity_type) VALUES ('messages')
ON CONFLICT (entity_type) DO NOTHING;

INSERT INTO s02_teamwork.sync_metadata (entity_type) VALUES ('tasks')
ON CONFLICT (entity_type) DO NOTHING;

INSERT INTO s02_teamwork.sync_metadata (entity_type) VALUES ('files')
ON CONFLICT (entity_type) DO NOTHING;

-- ============================================================================
-- WERYFIKACJA
-- ============================================================================

-- Sprawdź dodane kolumny w work_groups
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 's02_teamwork' 
  AND table_name = 'work_groups'
  AND column_name IN ('server_id', 'last_synced', 'sync_status', 'version', 'modified_locally')
ORDER BY ordinal_position;

-- Sprawdź wszystkie tabele w schemacie (powinno być 10 tabel)
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 's02_teamwork' 
ORDER BY table_name;

-- Oczekiwane tabele:
-- 1. work_groups
-- 2. group_members
-- 3. topics
-- 4. topic_members (nowa)
-- 5. messages
-- 6. tasks
-- 7. topic_files (nowa)
-- 8. topic_invitations (nowa)
-- 9. topic_share_links (nowa)
-- 10. sync_metadata (nowa)
-- 11. sync_conflicts (nowa)

-- Sprawdź metadane sync
SELECT * FROM s02_teamwork.sync_metadata;
