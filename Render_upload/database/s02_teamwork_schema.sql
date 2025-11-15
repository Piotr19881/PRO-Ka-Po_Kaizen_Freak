-- ============================================================================
-- SCHEMAT BAZY DANYCH - MODUŁ TEAMWORK (PostgreSQL)
-- ============================================================================
-- Kompletna struktura tabel dla modułu współpracy zespołowej
-- Schema: s02_teamwork
-- Includes: Phase 1-6 features + sync metadata + collaboration features
-- ============================================================================

-- Utwórz schemat
CREATE SCHEMA IF NOT EXISTS s02_teamwork;

COMMENT ON SCHEMA s02_teamwork IS 'Moduł współpracy zespołowej - grupy, tematy, wiadomości, zadania, pliki';

-- Ustaw schemat roboczy
SET search_path TO s02_teamwork;

-- ============================================================================
-- TABELA: work_groups
-- ============================================================================
CREATE TABLE IF NOT EXISTS s02_teamwork.work_groups (
    group_id SERIAL PRIMARY KEY,
    group_name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Sync metadata (Phase 5)
    server_id INTEGER,
    last_synced TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    modified_locally BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE s02_teamwork.work_groups IS 'Grupy robocze - kontener dla tematów i członków';
COMMENT ON COLUMN s02_teamwork.work_groups.sync_status IS 'Status synchronizacji: pending, synced, conflict, error';
COMMENT ON COLUMN s02_teamwork.work_groups.version IS 'Wersja dla rozwiązywania konfliktów';

-- ============================================================================
-- TABELA: group_members
-- ============================================================================
CREATE TABLE IF NOT EXISTS s02_teamwork.group_members (
    group_member_id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES s02_teamwork.work_groups(group_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'member')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(group_id, user_id)
);

COMMENT ON TABLE s02_teamwork.group_members IS 'Członkowie grup roboczych z rolami';

-- ============================================================================
-- TABELA: topics
-- ============================================================================
CREATE TABLE IF NOT EXISTS s02_teamwork.topics (
    topic_id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES s02_teamwork.work_groups(group_id) ON DELETE CASCADE,
    topic_name VARCHAR(300) NOT NULL,
    created_by TEXT NOT NULL REFERENCES s01_user_accounts.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Sync metadata (Phase 5)
    server_id INTEGER,
    last_synced TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    modified_locally BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE s02_teamwork.topics IS 'Wątki tematyczne w grupach';

-- ============================================================================
-- TABELA: topic_members (Phase 6 - collaboration)
-- ============================================================================
CREATE TABLE IF NOT EXISTS s02_teamwork.topic_members (
    topic_member_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'viewer' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(topic_id, user_id)
);

COMMENT ON TABLE s02_teamwork.topic_members IS 'Członkowie wątków z rozszerzonymi rolami (Phase 6)';
COMMENT ON COLUMN s02_teamwork.topic_members.role IS 'Rola: owner (pełne uprawnienia), admin (zarządzanie), member (edycja), viewer (tylko odczyt)';

-- ============================================================================
-- TABELA: messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS s02_teamwork.messages (
    message_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id),
    content TEXT NOT NULL,
    background_color VARCHAR(7) DEFAULT '#FFFFFF',
    is_important BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    edited_at TIMESTAMP WITH TIME ZONE,
    
    -- Sync metadata (Phase 5)
    server_id INTEGER,
    last_synced TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    modified_locally BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE s02_teamwork.messages IS 'Wiadomości w wątkach tematycznych';

-- ============================================================================
-- TABELA: tasks
-- ============================================================================
CREATE TABLE IF NOT EXISTS s02_teamwork.tasks (
    task_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES s02_teamwork.topics(topic_id) ON DELETE CASCADE,
    task_subject VARCHAR(500) NOT NULL,
    task_description TEXT,
    assigned_to TEXT REFERENCES s01_user_accounts.users(id),
    created_by TEXT NOT NULL REFERENCES s01_user_accounts.users(id),
    due_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed BOOLEAN DEFAULT FALSE,
    completed_by TEXT REFERENCES s01_user_accounts.users(id),
    completed_at TIMESTAMP WITH TIME ZONE,
    is_important BOOLEAN DEFAULT FALSE,
    
    -- Sync metadata (Phase 5)
    server_id INTEGER,
    last_synced TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'pending',
    version INTEGER DEFAULT 1,
    modified_locally BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE s02_teamwork.tasks IS 'Zadania przypisane do wątków';

-- ============================================================================
-- TABELA: topic_files (Phase 2 - Backblaze B2 integration)
-- ============================================================================
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
COMMENT ON COLUMN s02_teamwork.topic_files.b2_file_id IS 'Unikalny ID pliku w Backblaze B2';
COMMENT ON COLUMN s02_teamwork.topic_files.download_url IS 'Publiczny URL do pobrania pliku';

-- ============================================================================
-- TABELA: topic_invitations (Phase 6 - collaboration)
-- ============================================================================
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
COMMENT ON COLUMN s02_teamwork.topic_invitations.token IS 'Unikalny token zaproszenia do weryfikacji';

-- ============================================================================
-- TABELA: topic_share_links (Phase 6 - collaboration)
-- ============================================================================
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
COMMENT ON COLUMN s02_teamwork.topic_share_links.max_uses IS 'Maksymalna liczba użyć (NULL = bez limitu)';

-- ============================================================================
-- TABELA: sync_metadata (Phase 5)
-- ============================================================================
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

COMMENT ON TABLE s02_teamwork.sync_metadata IS 'Globalne metadane synchronizacji dla każdego typu encji';
COMMENT ON COLUMN s02_teamwork.sync_metadata.entity_type IS 'Typ: groups, topics, messages, tasks, files';

-- ============================================================================
-- TABELA: sync_conflicts (Phase 5)
-- ============================================================================
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

COMMENT ON TABLE s02_teamwork.sync_conflicts IS 'Rejestr konfliktów synchronizacji z lokalnymi danymi';
COMMENT ON COLUMN s02_teamwork.sync_conflicts.local_data IS 'JSON z danymi lokalnymi';
COMMENT ON COLUMN s02_teamwork.sync_conflicts.server_data IS 'JSON z danymi z serwera';

-- ============================================================================
-- INDEKSY DLA WYDAJNOŚCI
-- ============================================================================

-- Work Groups
CREATE INDEX IF NOT EXISTS idx_groups_created_by ON s02_teamwork.work_groups(created_by);
CREATE INDEX IF NOT EXISTS idx_groups_active ON s02_teamwork.work_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_groups_sync ON s02_teamwork.work_groups(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_groups_server ON s02_teamwork.work_groups(server_id);

-- Group Members
CREATE INDEX IF NOT EXISTS idx_group_members_user ON s02_teamwork.group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group ON s02_teamwork.group_members(group_id);

-- Topics
CREATE INDEX IF NOT EXISTS idx_topics_group ON s02_teamwork.topics(group_id);
CREATE INDEX IF NOT EXISTS idx_topics_created_by ON s02_teamwork.topics(created_by);
CREATE INDEX IF NOT EXISTS idx_topics_active ON s02_teamwork.topics(is_active);
CREATE INDEX IF NOT EXISTS idx_topics_sync ON s02_teamwork.topics(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_topics_server ON s02_teamwork.topics(server_id);

-- Topic Members
CREATE INDEX IF NOT EXISTS idx_topic_members_user ON s02_teamwork.topic_members(user_id);
CREATE INDEX IF NOT EXISTS idx_topic_members_topic ON s02_teamwork.topic_members(topic_id);

-- Messages
CREATE INDEX IF NOT EXISTS idx_messages_topic ON s02_teamwork.messages(topic_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON s02_teamwork.messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON s02_teamwork.messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_important ON s02_teamwork.messages(is_important) WHERE is_important = TRUE;
CREATE INDEX IF NOT EXISTS idx_messages_sync ON s02_teamwork.messages(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_messages_server ON s02_teamwork.messages(server_id);

-- Tasks
CREATE INDEX IF NOT EXISTS idx_tasks_topic ON s02_teamwork.tasks(topic_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON s02_teamwork.tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_created_by ON s02_teamwork.tasks(created_by);
CREATE INDEX IF NOT EXISTS idx_tasks_completed ON s02_teamwork.tasks(completed);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON s02_teamwork.tasks(due_date) WHERE completed = FALSE;
CREATE INDEX IF NOT EXISTS idx_tasks_important ON s02_teamwork.tasks(is_important) WHERE is_important = TRUE;
CREATE INDEX IF NOT EXISTS idx_tasks_sync ON s02_teamwork.tasks(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_tasks_server ON s02_teamwork.tasks(server_id);

-- Topic Files
CREATE INDEX IF NOT EXISTS idx_files_topic ON s02_teamwork.topic_files(topic_id);
CREATE INDEX IF NOT EXISTS idx_files_uploaded_by ON s02_teamwork.topic_files(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_files_important ON s02_teamwork.topic_files(is_important) WHERE is_important = TRUE;
CREATE INDEX IF NOT EXISTS idx_files_sync ON s02_teamwork.topic_files(sync_status, modified_locally);
CREATE INDEX IF NOT EXISTS idx_files_server ON s02_teamwork.topic_files(server_id);

-- Invitations
CREATE INDEX IF NOT EXISTS idx_invitations_topic ON s02_teamwork.topic_invitations(topic_id);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON s02_teamwork.topic_invitations(invited_email);
CREATE INDEX IF NOT EXISTS idx_invitations_status ON s02_teamwork.topic_invitations(status);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON s02_teamwork.topic_invitations(token);

-- Share Links
CREATE INDEX IF NOT EXISTS idx_share_links_topic ON s02_teamwork.topic_share_links(topic_id);
CREATE INDEX IF NOT EXISTS idx_share_links_token ON s02_teamwork.topic_share_links(token);
CREATE INDEX IF NOT EXISTS idx_share_links_active ON s02_teamwork.topic_share_links(is_active) WHERE is_active = TRUE;

-- Sync Conflicts
CREATE INDEX IF NOT EXISTS idx_conflicts_unresolved ON s02_teamwork.sync_conflicts(entity_type, resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_conflicts_entity ON s02_teamwork.sync_conflicts(entity_type, entity_server_id);

-- ============================================================================
-- TRIGGERY DO AUTOMATYCZNEGO OZNACZANIA ZMIAN (Phase 5)
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
-- INICJALIZACJA METADANYCH SYNCHRONIZACJI
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
-- WERYFIKACJA STRUKTURY
-- ============================================================================

-- Po wykonaniu tego skryptu zweryfikuj strukturę:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 's02_teamwork' ORDER BY table_name;
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 's02_teamwork' AND table_name = 'work_groups';
