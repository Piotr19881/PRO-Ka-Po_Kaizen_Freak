-- ============================================================================
-- SCHEMA: s06_notes
-- PRO-Ka-Po Notes Module - PostgreSQL Schema
-- Local-First Architecture with Sync Support
-- ============================================================================

-- Utwórz schemat
CREATE SCHEMA IF NOT EXISTS s06_notes;

-- ============================================================================
-- TABLE: notes
-- Główna tabela notatek z obsługą hierarchii (parent-child) i synchronizacji
-- ============================================================================

CREATE TABLE s06_notes.notes (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Foreign key do użytkownika
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Hierarchia (parent-child relationship)
    -- NULL = notatka główna (root)
    -- NOT NULL = podnotatka (child)
    parent_id TEXT REFERENCES s06_notes.notes(id) ON DELETE CASCADE,
    
    -- Dane notatki
    title TEXT NOT NULL CHECK (length(title) > 0 AND length(title) <= 500),
    content TEXT, -- HTML z formatowaniem (max ~100KB recommended)
    color TEXT DEFAULT '#1976D2' CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    sort_order INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Soft delete (synchronizacja wymaga zachowania usuniętych rekordów)
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    synced_at TIMESTAMP, -- Ostatnia synchronizacja z klientem
    version INTEGER DEFAULT 1 NOT NULL CHECK (version >= 1), -- Conflict resolution
    
    -- Constraints
    CONSTRAINT notes_parent_not_self CHECK (id != parent_id)
);

-- ============================================================================
-- TABLE: note_links
-- Hiperłącza między notatkami (zaznaczony tekst → podnotatka)
-- ============================================================================

CREATE TABLE s06_notes.note_links (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Relations
    source_note_id TEXT NOT NULL REFERENCES s06_notes.notes(id) ON DELETE CASCADE,
    target_note_id TEXT NOT NULL REFERENCES s06_notes.notes(id) ON DELETE CASCADE,
    
    -- Link data
    link_text TEXT NOT NULL CHECK (length(link_text) > 0 AND length(link_text) <= 500),
    start_position INTEGER NOT NULL CHECK (start_position >= 0),
    end_position INTEGER NOT NULL CHECK (end_position >= start_position),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Sync metadata
    version INTEGER DEFAULT 1 NOT NULL CHECK (version >= 1),
    
    -- Constraints
    CONSTRAINT links_not_self CHECK (source_note_id != target_note_id),
    CONSTRAINT links_position_valid CHECK (end_position > start_position)
);

-- ============================================================================
-- INDEXES dla wydajności
-- ============================================================================

-- Indeks dla pobierania notatek użytkownika (główne queries)
CREATE INDEX idx_notes_user_deleted ON s06_notes.notes(user_id, deleted_at);

-- Indeks dla hierarchii (pobieranie children)
CREATE INDEX idx_notes_parent_order ON s06_notes.notes(parent_id, sort_order) 
    WHERE deleted_at IS NULL;

-- Indeks dla ostatnio modyfikowanych (synchronizacja)
CREATE INDEX idx_notes_updated ON s06_notes.notes(updated_at DESC);

-- Indeks dla ulubionych
CREATE INDEX idx_notes_favorites ON s06_notes.notes(user_id, is_favorite) 
    WHERE is_favorite = TRUE AND deleted_at IS NULL;

-- Indeks dla wyszukiwania po tytule (LIKE queries)
CREATE INDEX idx_notes_title_search ON s06_notes.notes(user_id, title) 
    WHERE deleted_at IS NULL;

-- Indeksy dla note_links
CREATE INDEX idx_links_source ON s06_notes.note_links(source_note_id);
CREATE INDEX idx_links_target ON s06_notes.note_links(target_note_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Auto-update updated_at przy każdej zmianie
CREATE OR REPLACE FUNCTION s06_notes.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_notes_updated_at 
    BEFORE UPDATE ON s06_notes.notes
    FOR EACH ROW 
    EXECUTE FUNCTION s06_notes.update_updated_at_column();

-- Trigger: Increment version przy każdej zmianie (conflict resolution)
CREATE OR REPLACE FUNCTION s06_notes.increment_version_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Tylko jeśli zmieniono rzeczywiste dane (nie metadata sync)
    IF (OLD.title IS DISTINCT FROM NEW.title OR 
        OLD.content IS DISTINCT FROM NEW.content OR
        OLD.color IS DISTINCT FROM NEW.color OR
        OLD.parent_id IS DISTINCT FROM NEW.parent_id OR
        OLD.is_favorite IS DISTINCT FROM NEW.is_favorite OR
        OLD.deleted_at IS DISTINCT FROM NEW.deleted_at) THEN
        NEW.version = OLD.version + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_notes_increment_version
    BEFORE UPDATE ON s06_notes.notes
    FOR EACH ROW
    EXECUTE FUNCTION s06_notes.increment_version_column();

-- Trigger: Zapobiegaj cyklom w hierarchii (np. A->B->C->A)
CREATE OR REPLACE FUNCTION s06_notes.prevent_circular_reference()
RETURNS TRIGGER AS $$
DECLARE
    current_parent TEXT;
    depth INTEGER := 0;
    max_depth INTEGER := 100; -- Max głębokość zagnieżdżenia
BEGIN
    -- Jeśli nie ma parent_id, ok
    IF NEW.parent_id IS NULL THEN
        RETURN NEW;
    END IF;
    
    -- Sprawdź czy parent istnieje
    IF NOT EXISTS (SELECT 1 FROM s06_notes.notes WHERE id = NEW.parent_id) THEN
        RAISE EXCEPTION 'Parent note does not exist: %', NEW.parent_id;
    END IF;
    
    -- Sprawdź cykl
    current_parent := NEW.parent_id;
    
    WHILE current_parent IS NOT NULL AND depth < max_depth LOOP
        -- Wykryto cykl!
        IF current_parent = NEW.id THEN
            RAISE EXCEPTION 'Circular reference detected: note % cannot be its own ancestor', NEW.id;
        END IF;
        
        -- Idź w górę hierarchii
        SELECT parent_id INTO current_parent 
        FROM s06_notes.notes 
        WHERE id = current_parent;
        
        depth := depth + 1;
    END LOOP;
    
    -- Zbyt głęboka hierarchia
    IF depth >= max_depth THEN
        RAISE EXCEPTION 'Maximum nesting depth (%) exceeded', max_depth;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_notes_prevent_circular
    BEFORE INSERT OR UPDATE ON s06_notes.notes
    FOR EACH ROW
    EXECUTE FUNCTION s06_notes.prevent_circular_reference();

-- ============================================================================
-- VIEWS (opcjonalne - dla wygody)
-- ============================================================================

-- View: Aktywne notatki (nie usunięte)
CREATE OR REPLACE VIEW s06_notes.active_notes AS
SELECT * FROM s06_notes.notes
WHERE deleted_at IS NULL;

-- View: Notatki główne (root notes)
CREATE OR REPLACE VIEW s06_notes.root_notes AS
SELECT * FROM s06_notes.notes
WHERE parent_id IS NULL AND deleted_at IS NULL
ORDER BY sort_order, created_at DESC;

-- View: Statystyki użytkownika
CREATE OR REPLACE VIEW s06_notes.user_stats AS
SELECT 
    user_id,
    COUNT(*) FILTER (WHERE deleted_at IS NULL) as total_notes,
    COUNT(*) FILTER (WHERE deleted_at IS NULL AND parent_id IS NULL) as root_notes,
    COUNT(*) FILTER (WHERE is_favorite = TRUE AND deleted_at IS NULL) as favorite_notes,
    MAX(updated_at) as last_update
FROM s06_notes.notes
GROUP BY user_id;

-- ============================================================================
-- FUNCTIONS (pomocnicze)
-- ============================================================================

-- Function: Pobierz całą ścieżkę hierarchii (breadcrumb)
CREATE OR REPLACE FUNCTION s06_notes.get_note_path(note_id_param TEXT)
RETURNS TABLE(id TEXT, title TEXT, level INTEGER) AS $$
WITH RECURSIVE note_path AS (
    -- Punkt startowy
    SELECT n.id, n.title, n.parent_id, 0 as level
    FROM s06_notes.notes n
    WHERE n.id = note_id_param
    
    UNION ALL
    
    -- Rekurencja w górę
    SELECT n.id, n.title, n.parent_id, np.level + 1
    FROM s06_notes.notes n
    INNER JOIN note_path np ON n.id = np.parent_id
)
SELECT id, title, level
FROM note_path
ORDER BY level DESC;
$$ LANGUAGE sql;

-- Function: Pobierz wszystkie dzieci (rekurencyjnie)
CREATE OR REPLACE FUNCTION s06_notes.get_note_descendants(note_id_param TEXT)
RETURNS TABLE(id TEXT, title TEXT, parent_id TEXT, level INTEGER) AS $$
WITH RECURSIVE descendants AS (
    -- Punkt startowy
    SELECT n.id, n.title, n.parent_id, 0 as level
    FROM s06_notes.notes n
    WHERE n.id = note_id_param
    
    UNION ALL
    
    -- Rekurencja w dół
    SELECT n.id, n.title, n.parent_id, d.level + 1
    FROM s06_notes.notes n
    INNER JOIN descendants d ON n.parent_id = d.id
    WHERE n.deleted_at IS NULL
)
SELECT id, title, parent_id, level
FROM descendants
WHERE level > 0 -- Exclude the starting note
ORDER BY level, title;
$$ LANGUAGE sql;

-- Function: Soft delete z cascade (usuwa wszystkie dzieci)
CREATE OR REPLACE FUNCTION s06_notes.soft_delete_note_cascade(note_id_param TEXT)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Soft delete notatki i wszystkich jej potomków
    WITH RECURSIVE descendants AS (
        SELECT id FROM s06_notes.notes WHERE id = note_id_param
        UNION ALL
        SELECT n.id FROM s06_notes.notes n
        INNER JOIN descendants d ON n.parent_id = d.id
    )
    UPDATE s06_notes.notes
    SET deleted_at = CURRENT_TIMESTAMP
    WHERE id IN (SELECT id FROM descendants) AND deleted_at IS NULL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA (opcjonalne - przykładowe dane testowe)
-- ============================================================================

-- Dodaj przykładową notatkę dla celów testowych (usuń w produkcji)
-- INSERT INTO s06_notes.notes (id, user_id, title, content, color)
-- VALUES (
--     'test-note-1',
--     'test-user-id', 
--     'Przykładowa notatka',
--     '<p>To jest <b>przykładowa</b> notatka z <i>formatowaniem</i>.</p>',
--     '#1976D2'
-- );

-- ============================================================================
-- GRANTS (uprawnienia)
-- ============================================================================

-- Grant dla użytkownika aplikacji (jeśli używasz dedykowanego usera)
-- GRANT USAGE ON SCHEMA s06_notes TO pro_ka_po_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA s06_notes TO pro_ka_po_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA s06_notes TO pro_ka_po_user;

-- ============================================================================
-- KONIEC SCHEMATU
-- ============================================================================

-- Sprawdź czy wszystko utworzone poprawnie
SELECT 
    'Schema s06_notes created successfully!' as status,
    COUNT(*) FILTER (WHERE table_schema = 's06_notes' AND table_type = 'BASE TABLE') as tables_count,
    COUNT(*) FILTER (WHERE table_schema = 's06_notes' AND table_type = 'VIEW') as views_count
FROM information_schema.tables
WHERE table_schema = 's06_notes';

-- Pokaż wszystkie tabele w schemacie
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) as columns_count
FROM information_schema.tables t
WHERE table_schema = 's06_notes' AND table_type = 'BASE TABLE'
ORDER BY table_name;
