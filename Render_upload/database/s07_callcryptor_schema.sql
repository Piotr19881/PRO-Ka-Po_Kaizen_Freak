-- ============================================================
-- Schema: s07_callcryptor
-- Synchronizacja modułu CallCryptor
-- Created: 2025-11-09
-- Description: Schema dla synchronizacji nagrań CallCryptor
--              TYLKO METADANE - pliki audio pozostają lokalne
-- ============================================================

CREATE SCHEMA IF NOT EXISTS s07_callcryptor;

-- ============================================================
-- TABLE: recording_sources
-- Źródła nagrań (foldery lokalne lub konta email)
-- ============================================================
CREATE TABLE IF NOT EXISTS s07_callcryptor.recording_sources (
    -- Identyfikatory
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Podstawowe info
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('folder', 'email')),
    
    -- Opcje dla folder
    folder_path TEXT,
    file_extensions JSONB,              -- ["mp3", "wav", "m4a"]
    scan_depth INTEGER DEFAULT 1,
    
    -- Opcje dla email
    email_account_id TEXT,              -- Reference do email_accounts (inna baza)
    search_phrase TEXT,
    search_type TEXT DEFAULT 'SUBJECT', -- SUBJECT, ALL, BODY
    search_all_folders BOOLEAN DEFAULT FALSE,
    target_folder TEXT DEFAULT 'INBOX',
    attachment_pattern TEXT,
    contact_ignore_words TEXT,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    last_scan_at TIMESTAMP,
    recordings_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1,
    
    CONSTRAINT unique_source_name UNIQUE(user_id, source_name, deleted_at)
);

-- ============================================================
-- TABLE: recordings
-- Metadane nagrań (BEZ plików audio!)
-- ============================================================
CREATE TABLE IF NOT EXISTS s07_callcryptor.recordings (
    -- Identyfikatory
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES s07_callcryptor.recording_sources(id) ON DELETE CASCADE,
    
    -- Info o pliku (NIE synchronizujemy file_path!)
    file_name TEXT NOT NULL,
    file_size BIGINT,                   -- Bytes
    file_hash TEXT,                     -- MD5/SHA256 dla deduplication
    
    -- Info z e-mail (jeśli applicable)
    email_message_id TEXT,
    email_subject TEXT,
    email_sender TEXT,
    
    -- Metadata nagrania
    contact_name TEXT,
    contact_phone TEXT,
    duration INTEGER,                   -- Sekundy
    recording_date TIMESTAMP,
    
    -- Organizacja
    tags JSONB,                         -- ["tag1", "tag2"]
    notes TEXT,
    
    -- Transkrypcja
    transcription_status TEXT DEFAULT 'pending' 
        CHECK(transcription_status IN ('pending', 'processing', 'completed', 'failed')),
    transcription_text TEXT,
    transcription_language TEXT,
    transcription_confidence REAL,
    transcription_date TIMESTAMP,
    transcription_error TEXT,
    
    -- AI Summary
    ai_summary_status TEXT DEFAULT 'pending'
        CHECK(ai_summary_status IN ('pending', 'processing', 'completed', 'failed')),
    ai_summary_text TEXT,
    ai_summary_date TIMESTAMP,
    ai_summary_error TEXT,
    ai_summary_tasks JSONB,             -- [{"title": "...", "priority": "..."}]
    ai_key_points JSONB,                -- ["punkt1", "punkt2"]
    ai_action_items JSONB,              -- [{"action": "...", "priority": "..."}]
    
    -- Linki do innych modułów
    note_id UUID,
    task_id UUID,
    
    -- Flags
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP,
    archive_reason TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,
    favorited_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1
);

-- ============================================================
-- TABLE: recording_tags
-- Globalne tagi dla organizacji nagrań
-- ============================================================
CREATE TABLE IF NOT EXISTS s07_callcryptor.recording_tags (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    tag_name TEXT NOT NULL,
    tag_color TEXT DEFAULT '#2196F3',
    tag_icon TEXT,
    usage_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1,
    
    CONSTRAINT unique_tag_name UNIQUE(user_id, tag_name, deleted_at)
);

-- ============================================================
-- INDEXES
-- ============================================================

-- recording_sources
CREATE INDEX idx_sources_user ON s07_callcryptor.recording_sources(user_id);
CREATE INDEX idx_sources_type ON s07_callcryptor.recording_sources(source_type);
CREATE INDEX idx_sources_active ON s07_callcryptor.recording_sources(is_active);
CREATE INDEX idx_sources_deleted ON s07_callcryptor.recording_sources(deleted_at);

-- recordings
CREATE INDEX idx_recordings_user ON s07_callcryptor.recordings(user_id);
CREATE INDEX idx_recordings_source ON s07_callcryptor.recordings(source_id);
CREATE INDEX idx_recordings_date ON s07_callcryptor.recordings(recording_date DESC);
CREATE INDEX idx_recordings_contact ON s07_callcryptor.recordings(contact_name);
CREATE INDEX idx_recordings_trans_status ON s07_callcryptor.recordings(transcription_status);
CREATE INDEX idx_recordings_ai_status ON s07_callcryptor.recordings(ai_summary_status);
CREATE INDEX idx_recordings_archived ON s07_callcryptor.recordings(is_archived);
CREATE INDEX idx_recordings_favorite ON s07_callcryptor.recordings(is_favorite);
CREATE INDEX idx_recordings_hash ON s07_callcryptor.recordings(file_hash);
CREATE INDEX idx_recordings_deleted ON s07_callcryptor.recordings(deleted_at);
CREATE INDEX idx_recordings_updated ON s07_callcryptor.recordings(updated_at DESC);

-- recording_tags
CREATE INDEX idx_tags_user ON s07_callcryptor.recording_tags(user_id);
CREATE INDEX idx_tags_name ON s07_callcryptor.recording_tags(tag_name);
CREATE INDEX idx_tags_deleted ON s07_callcryptor.recording_tags(deleted_at);

-- ============================================================
-- TRIGGERS - Auto-update updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION s07_callcryptor.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sources_updated_at
    BEFORE UPDATE ON s07_callcryptor.recording_sources
    FOR EACH ROW
    EXECUTE FUNCTION s07_callcryptor.update_updated_at();

CREATE TRIGGER recordings_updated_at
    BEFORE UPDATE ON s07_callcryptor.recordings
    FOR EACH ROW
    EXECUTE FUNCTION s07_callcryptor.update_updated_at();

CREATE TRIGGER tags_updated_at
    BEFORE UPDATE ON s07_callcryptor.recording_tags
    FOR EACH ROW
    EXECUTE FUNCTION s07_callcryptor.update_updated_at();

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON SCHEMA s07_callcryptor IS 'Schema dla synchronizacji modułu CallCryptor - TYLKO metadane, pliki audio lokalne';
COMMENT ON TABLE s07_callcryptor.recording_sources IS 'Źródła nagrań (foldery lub konta email)';
COMMENT ON TABLE s07_callcryptor.recordings IS 'Metadane nagrań - pliki audio NIE SĄ synchronizowane!';
COMMENT ON TABLE s07_callcryptor.recording_tags IS 'Globalne tagi dla organizacji nagrań';
COMMENT ON COLUMN s07_callcryptor.recordings.file_hash IS 'Hash pliku dla deduplication - NIE synchronizujemy plików!';
