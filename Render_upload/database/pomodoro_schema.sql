-- =====================================================
-- PRO-Ka-Po Kaizen Freak - Pomodoro Module Database Schema
-- Schema: s05_pomodoro
-- Purpose: Przechowywanie tematów sesji i logów Pomodoro
-- =====================================================

-- Usuń istniejący schemat jeśli istnieje (OPCJONALNE - użyj ostrożnie!)
-- DROP SCHEMA IF EXISTS s05_pomodoro CASCADE;

-- Stwórz nowy schemat
CREATE SCHEMA IF NOT EXISTS s05_pomodoro;

-- =====================================================
-- Tabela 1: TEMATY SESJI (Session Topics)
-- Predefiniowane tematy do przypisywania sesji Pomodoro
-- =====================================================

CREATE TABLE IF NOT EXISTS s05_pomodoro.session_topics (
    -- Identyfikatory
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Dane tematu
    name VARCHAR(100) NOT NULL,                    -- Nazwa tematu (np. "Praca - Projekt X")
    color VARCHAR(7) DEFAULT '#FF6B6B',            -- Kolor w formacie HEX (dla UI)
    icon VARCHAR(50) DEFAULT '📚',                 -- Emoji lub nazwa ikony
    description TEXT,                               -- Opcjonalny opis
    
    -- Statystyki (obliczane automatycznie z logów)
    total_sessions INTEGER DEFAULT 0,               -- Liczba sesji z tym tematem
    total_work_time INTEGER DEFAULT 0,              -- Suma czasu pracy (minuty)
    total_break_time INTEGER DEFAULT 0,             -- Suma czasu przerw (minuty)
    
    -- Kolejność i widoczność
    sort_order INTEGER DEFAULT 0,                   -- Kolejność wyświetlania
    is_active BOOLEAN DEFAULT true,                 -- Czy temat jest aktywny
    is_favorite BOOLEAN DEFAULT false,              -- Czy temat jest ulubiony
    
    -- Metadane synchronizacji
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP WITH TIME ZONE,             -- Ostatnia synchronizacja z serwerem
    deleted_at TIMESTAMP WITH TIME ZONE,            -- Soft delete
    version INTEGER DEFAULT 1,                      -- Wersja dla conflict resolution
    
    -- Constraints
    CONSTRAINT topic_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT valid_color CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    CONSTRAINT valid_version CHECK (version > 0)
);

-- Indeksy dla wydajności
CREATE INDEX idx_session_topics_user_id ON s05_pomodoro.session_topics(user_id);
CREATE INDEX idx_session_topics_user_active ON s05_pomodoro.session_topics(user_id, is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_session_topics_created ON s05_pomodoro.session_topics(created_at DESC);
CREATE INDEX idx_session_topics_favorite ON s05_pomodoro.session_topics(user_id, is_favorite) WHERE is_favorite = true AND deleted_at IS NULL;

-- =====================================================
-- Tabela 2: LOGI SESJI (Session Logs)
-- Historia wykonanych sesji Pomodoro
-- =====================================================

CREATE TABLE IF NOT EXISTS s05_pomodoro.session_logs (
    -- Identyfikatory
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    topic_id UUID,                                  -- FK do session_topics (nullable - może być bez tematu)
    
    -- Dane czasowe sesji
    session_date DATE NOT NULL,                     -- Data wykonania sesji
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,   -- Początek sesji
    ended_at TIMESTAMP WITH TIME ZONE,              -- Koniec sesji (nullable jeśli przerwana)
    
    -- Czasy trwania (w minutach)
    work_duration INTEGER NOT NULL,                 -- Planowany czas pracy
    short_break_duration INTEGER,                   -- Planowany czas krótkiej przerwy
    long_break_duration INTEGER,                    -- Planowany czas długiej przerwy
    actual_work_time INTEGER,                       -- Rzeczywisty czas pracy (jeśli skończona)
    actual_break_time INTEGER,                      -- Rzeczywisty czas przerwy
    
    -- Status i typ sesji
    session_type VARCHAR(20) NOT NULL DEFAULT 'work',  -- 'work', 'short_break', 'long_break'
    status VARCHAR(20) NOT NULL DEFAULT 'completed',   -- 'completed', 'interrupted', 'skipped'
    pomodoro_count INTEGER DEFAULT 1,               -- Który pomodoro w cyklu (1-4)
    
    -- Dodatkowe dane
    notes TEXT,                                     -- Notatki użytkownika
    tags TEXT[],                                    -- Tagi (array) dla filtrowania
    productivity_rating INTEGER,                    -- Ocena produktywności (1-5)
    
    -- Metadane
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    version INTEGER DEFAULT 1,
    
    -- Constraints
    CONSTRAINT valid_session_type CHECK (session_type IN ('work', 'short_break', 'long_break')),
    CONSTRAINT valid_status CHECK (status IN ('completed', 'interrupted', 'skipped')),
    CONSTRAINT valid_durations CHECK (
        work_duration > 0 AND 
        (short_break_duration IS NULL OR short_break_duration > 0) AND
        (long_break_duration IS NULL OR long_break_duration > 0)
    ),
    CONSTRAINT valid_pomodoro_count CHECK (pomodoro_count BETWEEN 1 AND 4),
    CONSTRAINT valid_rating CHECK (productivity_rating IS NULL OR productivity_rating BETWEEN 1 AND 5),
    CONSTRAINT ended_after_started CHECK (ended_at IS NULL OR ended_at >= started_at),
    CONSTRAINT valid_version_log CHECK (version > 0),
    
    -- Foreign Key (z ON DELETE SET NULL bo topic może być usunięty)
    CONSTRAINT fk_session_logs_topic 
        FOREIGN KEY (topic_id) 
        REFERENCES s05_pomodoro.session_topics(id) 
        ON DELETE SET NULL
);

-- Indeksy dla wydajności zapytań
CREATE INDEX idx_session_logs_user_id ON s05_pomodoro.session_logs(user_id);
CREATE INDEX idx_session_logs_user_date ON s05_pomodoro.session_logs(user_id, session_date DESC);
CREATE INDEX idx_session_logs_topic ON s05_pomodoro.session_logs(topic_id) WHERE topic_id IS NOT NULL;
CREATE INDEX idx_session_logs_started ON s05_pomodoro.session_logs(started_at DESC);
CREATE INDEX idx_session_logs_user_active ON s05_pomodoro.session_logs(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_session_logs_status ON s05_pomodoro.session_logs(user_id, status) WHERE deleted_at IS NULL;

-- =====================================================
-- Triggery dla automatycznego UPDATE updated_at
-- =====================================================

-- Funkcja do aktualizacji updated_at
CREATE OR REPLACE FUNCTION s05_pomodoro.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger dla session_topics
CREATE TRIGGER update_session_topics_updated_at
    BEFORE UPDATE ON s05_pomodoro.session_topics
    FOR EACH ROW
    EXECUTE FUNCTION s05_pomodoro.update_updated_at_column();

-- Trigger dla session_logs
CREATE TRIGGER update_session_logs_updated_at
    BEFORE UPDATE ON s05_pomodoro.session_logs
    FOR EACH ROW
    EXECUTE FUNCTION s05_pomodoro.update_updated_at_column();

-- =====================================================
-- Funkcja do aktualizacji statystyk tematu
-- =====================================================

CREATE OR REPLACE FUNCTION s05_pomodoro.update_topic_statistics()
RETURNS TRIGGER AS $$
BEGIN
    -- Aktualizuj statystyki dla tematu jeśli istnieje topic_id
    IF NEW.topic_id IS NOT NULL AND NEW.status = 'completed' AND NEW.deleted_at IS NULL THEN
        UPDATE s05_pomodoro.session_topics
        SET 
            total_sessions = (
                SELECT COUNT(*) 
                FROM s05_pomodoro.session_logs 
                WHERE topic_id = NEW.topic_id 
                AND status = 'completed' 
                AND deleted_at IS NULL
            ),
            total_work_time = (
                SELECT COALESCE(SUM(actual_work_time), 0)
                FROM s05_pomodoro.session_logs 
                WHERE topic_id = NEW.topic_id 
                AND session_type = 'work'
                AND status = 'completed' 
                AND deleted_at IS NULL
            ),
            total_break_time = (
                SELECT COALESCE(SUM(actual_break_time), 0)
                FROM s05_pomodoro.session_logs 
                WHERE topic_id = NEW.topic_id 
                AND session_type IN ('short_break', 'long_break')
                AND status = 'completed' 
                AND deleted_at IS NULL
            )
        WHERE id = NEW.topic_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger do automatycznej aktualizacji statystyk
CREATE TRIGGER update_topic_stats_on_log_insert
    AFTER INSERT OR UPDATE ON s05_pomodoro.session_logs
    FOR EACH ROW
    EXECUTE FUNCTION s05_pomodoro.update_topic_statistics();

-- =====================================================
-- Przykładowe dane testowe (OPCJONALNE)
-- =====================================================

-- Usuń komentarz poniżej aby wstawić przykładowe dane
/*
-- Przykładowy użytkownik (zastąp prawdziwym UUID)
-- INSERT INTO s05_pomodoro.session_topics (user_id, name, color, icon, description, is_favorite)
-- VALUES 
--     ('00000000-0000-0000-0000-000000000001', 'Praca - Projekt A', '#FF6B6B', '💼', 'Główny projekt firmowy', true),
--     ('00000000-0000-0000-0000-000000000001', 'Nauka - Python', '#4ECDC4', '🐍', 'Kursy i tutorials Python', false),
--     ('00000000-0000-0000-0000-000000000001', 'Pisanie - Blog', '#95E1D3', '✍️', 'Artykuły na blog', false),
--     ('00000000-0000-0000-0000-000000000001', 'Sport', '#F38181', '🏃', 'Ćwiczenia i aktywność', false);
*/

-- =====================================================
-- Zapytania pomocnicze (Views)
-- =====================================================

-- Widok: Statystyki sesji per dzień
CREATE OR REPLACE VIEW s05_pomodoro.daily_statistics AS
SELECT 
    user_id,
    session_date,
    COUNT(*) FILTER (WHERE session_type = 'work' AND status = 'completed') as completed_pomodoros,
    SUM(actual_work_time) FILTER (WHERE session_type = 'work') as total_work_minutes,
    SUM(actual_break_time) FILTER (WHERE session_type IN ('short_break', 'long_break')) as total_break_minutes,
    COUNT(DISTINCT topic_id) FILTER (WHERE topic_id IS NOT NULL) as topics_worked_on,
    AVG(productivity_rating) FILTER (WHERE productivity_rating IS NOT NULL) as avg_productivity
FROM s05_pomodoro.session_logs
WHERE deleted_at IS NULL
GROUP BY user_id, session_date;

-- Widok: Top tematy (najbardziej używane)
CREATE OR REPLACE VIEW s05_pomodoro.top_topics AS
SELECT 
    t.user_id,
    t.id,
    t.name,
    t.color,
    t.icon,
    t.total_sessions,
    t.total_work_time,
    ROUND(t.total_work_time::numeric / NULLIF(t.total_sessions, 0), 2) as avg_session_time
FROM s05_pomodoro.session_topics t
WHERE t.deleted_at IS NULL AND t.is_active = true
ORDER BY t.total_sessions DESC, t.total_work_time DESC;

-- =====================================================
-- Uprawnienia (dostosuj do swojego użytkownika)
-- =====================================================

-- GRANT USAGE ON SCHEMA s05_pomodoro TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA s05_pomodoro TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA s05_pomodoro TO your_app_user;

-- =====================================================
-- Końcowe informacje
-- =====================================================

-- Sprawdź utworzone tabele
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 's05_pomodoro' AND table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 's05_pomodoro'
ORDER BY table_name;

COMMENT ON SCHEMA s05_pomodoro IS 'Schema for Pomodoro module - session topics and logs';
COMMENT ON TABLE s05_pomodoro.session_topics IS 'Predefiniowane tematy do przypisywania sesji Pomodoro';
COMMENT ON TABLE s05_pomodoro.session_logs IS 'Historia wykonanych sesji Pomodoro z czasami i statusami';
