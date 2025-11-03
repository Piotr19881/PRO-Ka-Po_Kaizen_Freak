-- ============================================================================
-- SCHEMAT BAZY DANYCH DLA MODUŁU ALARMÓW I TIMERÓW
-- Schema: s04_alarms_timers
-- Wersja: 1.0
-- Data: 2025-11-02
-- ============================================================================

-- Utworzenie schematu
CREATE SCHEMA IF NOT EXISTS s04_alarms_timers;

-- ============================================================================
-- TABELA: alarms_timers
-- Główna tabela przechowująca zarówno alarmy jak i timery
-- Unified approach - jedna tabela dla obu typów z rozróżnieniem przez typ
-- ============================================================================

CREATE TABLE IF NOT EXISTS s04_alarms_timers.alarms_timers (
    -- Identyfikatory i typ
    id TEXT PRIMARY KEY,  -- UUID generowane po stronie klienta
    user_id TEXT NOT NULL,  -- Referencja do s01_user_accounts.users(id)
    type TEXT NOT NULL,  -- 'alarm' lub 'timer'
    
    -- Wspólne pola
    label TEXT NOT NULL,  -- Etykieta/opis
    enabled BOOLEAN DEFAULT TRUE,  -- Czy aktywny
    play_sound BOOLEAN DEFAULT TRUE,  -- Czy odtwarzać dźwięk
    show_popup BOOLEAN DEFAULT TRUE,  -- Czy pokazać popup
    custom_sound TEXT,  -- Ścieżka/URL do niestandardowego dźwięku
    
    -- Pola specyficzne dla alarmów (NULL dla timerów)
    alarm_time TIME,  -- Godzina alarmu (HH:MM)
    recurrence TEXT,  -- 'once', 'daily', 'weekdays', 'weekends', 'custom'
    days INTEGER[],  -- Tablica dni tygodnia (0=Pon, 6=Nie)
    
    -- Pola specyficzne dla timerów (NULL dla alarmów)
    duration INTEGER,  -- Czas w sekundach
    remaining INTEGER,  -- Pozostały czas (NULL jeśli nie uruchomiony)
    repeat BOOLEAN,  -- Czy powtarzać timer
    started_at TIMESTAMP WITH TIME ZONE,  -- Kiedy uruchomiono timer
    
    -- Synchronizacja local-first
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete
    synced_at TIMESTAMP WITH TIME ZONE,  -- Ostatnia synchronizacja
    version INTEGER DEFAULT 1,  -- Wersja dla conflict resolution
    
    -- Walidacja
    CONSTRAINT alarms_timers_type_check CHECK (type IN ('alarm', 'timer')),
    CONSTRAINT alarms_timers_recurrence_check CHECK (
        recurrence IS NULL OR 
        recurrence IN ('once', 'daily', 'weekdays', 'weekends', 'custom')
    ),
    CONSTRAINT alarms_timers_alarm_fields CHECK (
        (type = 'alarm' AND alarm_time IS NOT NULL) OR
        (type = 'timer' AND duration IS NOT NULL)
    )
);

-- Indeksy dla optymalizacji zapytań
CREATE INDEX IF NOT EXISTS idx_alarms_timers_user_id 
    ON s04_alarms_timers.alarms_timers(user_id);
    
CREATE INDEX IF NOT EXISTS idx_alarms_timers_type 
    ON s04_alarms_timers.alarms_timers(type);
    
CREATE INDEX IF NOT EXISTS idx_alarms_timers_enabled 
    ON s04_alarms_timers.alarms_timers(enabled) 
    WHERE deleted_at IS NULL;
    
CREATE INDEX IF NOT EXISTS idx_alarms_timers_synced 
    ON s04_alarms_timers.alarms_timers(synced_at);
    
CREATE INDEX IF NOT EXISTS idx_alarms_timers_deleted 
    ON s04_alarms_timers.alarms_timers(deleted_at);
    
CREATE INDEX IF NOT EXISTS idx_alarms_timers_user_type 
    ON s04_alarms_timers.alarms_timers(user_id, type) 
    WHERE deleted_at IS NULL;

-- Komentarze dla dokumentacji
COMMENT ON SCHEMA s04_alarms_timers IS 'Moduł alarmów i timerów - local-first architecture';
COMMENT ON TABLE s04_alarms_timers.alarms_timers IS 'Unified table dla alarmów i timerów użytkowników';
COMMENT ON COLUMN s04_alarms_timers.alarms_timers.type IS 'Typ: alarm lub timer';
COMMENT ON COLUMN s04_alarms_timers.alarms_timers.recurrence IS 'Cykliczność alarmu: once, daily, weekdays, weekends, custom';
COMMENT ON COLUMN s04_alarms_timers.alarms_timers.days IS 'Dni tygodnia dla custom recurrence (0=Pon, 6=Nie)';
COMMENT ON COLUMN s04_alarms_timers.alarms_timers.version IS 'Wersja dla conflict resolution w sync';

-- ============================================================================
-- TRIGGER: Automatyczna aktualizacja updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION s04_alarms_timers.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_alarms_timers_updated_at 
    ON s04_alarms_timers.alarms_timers;
    
CREATE TRIGGER trigger_update_alarms_timers_updated_at
    BEFORE UPDATE ON s04_alarms_timers.alarms_timers
    FOR EACH ROW
    EXECUTE FUNCTION s04_alarms_timers.update_updated_at_column();

-- ============================================================================
-- PRZYKŁADOWE ZAPYTANIA (QUERIES)
-- ============================================================================

-- Pobranie wszystkich aktywnych alarmów użytkownika
/*
SELECT * FROM s04_alarms_timers.alarms_timers
WHERE user_id = 'user_uuid'
  AND type = 'alarm'
  AND deleted_at IS NULL
  AND enabled = TRUE
ORDER BY alarm_time ASC;
*/

-- Pobranie wszystkich aktywnych timerów użytkownika
/*
SELECT * FROM s04_alarms_timers.alarms_timers
WHERE user_id = 'user_uuid'
  AND type = 'timer'
  AND deleted_at IS NULL
ORDER BY created_at DESC;
*/

-- Pobranie elementów wymagających synchronizacji
/*
SELECT * FROM s04_alarms_timers.alarms_timers
WHERE user_id = 'user_uuid'
  AND (synced_at IS NULL OR updated_at > synced_at)
  AND deleted_at IS NULL;
*/

-- Soft delete (użytkownik usuwa alarm/timer)
/*
UPDATE s04_alarms_timers.alarms_timers
SET deleted_at = NOW(), 
    version = version + 1
WHERE id = 'item_uuid' 
  AND user_id = 'user_uuid';
*/

-- Oznaczenie jako zsynchronizowane
/*
UPDATE s04_alarms_timers.alarms_timers
SET synced_at = NOW()
WHERE id = 'item_uuid' 
  AND user_id = 'user_uuid';
*/

-- Pobranie alarmów na dziś (z uwzględnieniem recurrence)
/*
SELECT * FROM s04_alarms_timers.alarms_timers
WHERE user_id = 'user_uuid'
  AND type = 'alarm'
  AND enabled = TRUE
  AND deleted_at IS NULL
  AND (
    recurrence = 'daily' OR
    recurrence = 'once' OR
    (recurrence = 'weekdays' AND EXTRACT(DOW FROM NOW()) BETWEEN 1 AND 5) OR
    (recurrence = 'weekends' AND EXTRACT(DOW FROM NOW()) IN (0, 6)) OR
    (recurrence = 'custom' AND EXTRACT(DOW FROM NOW()) = ANY(days))
  )
ORDER BY alarm_time;
*/

-- Upsert (insert or update) dla synchronizacji
/*
INSERT INTO s04_alarms_timers.alarms_timers (
    id, user_id, type, label, enabled, alarm_time, 
    recurrence, days, play_sound, show_popup, 
    custom_sound, version, synced_at
) VALUES (
    $1, $2, 'alarm', $3, $4, $5, 
    $6, $7, $8, $9, 
    $10, 1, NOW()
)
ON CONFLICT (id) DO UPDATE SET
    label = EXCLUDED.label,
    enabled = EXCLUDED.enabled,
    alarm_time = EXCLUDED.alarm_time,
    recurrence = EXCLUDED.recurrence,
    days = EXCLUDED.days,
    play_sound = EXCLUDED.play_sound,
    show_popup = EXCLUDED.show_popup,
    custom_sound = EXCLUDED.custom_sound,
    updated_at = NOW(),
    synced_at = NOW(),
    version = s04_alarms_timers.alarms_timers.version + 1
WHERE s04_alarms_timers.alarms_timers.version < EXCLUDED.version;
*/

-- ============================================================================
-- UPRAWNIENIA (dostosuj do potrzeb)
-- ============================================================================

-- Przykład: nadanie uprawnień dla roli aplikacji
/*
GRANT USAGE ON SCHEMA s04_alarms_timers TO app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA s04_alarms_timers TO app_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA s04_alarms_timers TO app_role;
*/

-- ============================================================================
-- MIGRACJA DANYCH (jeśli są stare dane)
-- ============================================================================

/*
-- Przykład migracji z JSON files do PostgreSQL
-- Uruchom to dopiero gdy masz dane do migracji

-- INSERT INTO s04_alarms_timers.alarms_timers (...)
-- SELECT ... FROM ...
*/

-- ============================================================================
-- ROLLBACK (w razie potrzeby)
-- ============================================================================

/*
-- UWAGA: To usunie cały schemat i wszystkie dane!
-- DROP SCHEMA IF NOT EXISTS CASCADE;
*/

-- Przechowuje alarmy użytkowników z pełną synchronizacją local-first
CREATE TABLE IF NOT EXISTS s01_user_accounts.alarms (
    -- Identyfikatory
    id TEXT PRIMARY KEY,  -- UUID generowane po stronie klienta
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Dane alarmu
    time TIME NOT NULL,  -- Godzina alarmu (HH:MM)
    label TEXT NOT NULL,  -- Etykieta/opis alarmu
    enabled BOOLEAN DEFAULT TRUE,  -- Czy alarm jest włączony
    
    -- Cykliczność
    recurrence TEXT NOT NULL DEFAULT 'once',  -- once, daily, weekdays, weekends, custom
    days INTEGER[] DEFAULT '{}',  -- Tablica dni tygodnia (0=Poniedziałek, 6=Niedziela)
    
    -- Opcje
    play_sound BOOLEAN DEFAULT TRUE,  -- Czy odtwarzać dźwięk
    show_popup BOOLEAN DEFAULT TRUE,  -- Czy pokazać popup
    custom_sound TEXT,  -- Ścieżka/URL do niestandardowego dźwięku
    
    -- Synchronizacja local-first
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete
    synced_at TIMESTAMP WITH TIME ZONE,  -- Ostatnia synchronizacja
    version INTEGER DEFAULT 1,  -- Wersja dla conflict resolution
    
    -- Indeksy dla wydajności
    CONSTRAINT alarms_recurrence_check CHECK (recurrence IN ('once', 'daily', 'weekdays', 'weekends', 'custom'))
);

-- Indeksy dla optymalizacji zapytań
CREATE INDEX IF NOT EXISTS idx_alarms_user_id ON s01_user_accounts.alarms(user_id);
CREATE INDEX IF NOT EXISTS idx_alarms_enabled ON s01_user_accounts.alarms(enabled) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_alarms_synced ON s01_user_accounts.alarms(synced_at);
CREATE INDEX IF NOT EXISTS idx_alarms_deleted ON s01_user_accounts.alarms(deleted_at);


-- Tabela: timers
-- Przechowuje timery użytkowników z pełną synchronizacją local-first
CREATE TABLE IF NOT EXISTS s01_user_accounts.timers (
    -- Identyfikatory
    id TEXT PRIMARY KEY,  -- UUID generowane po stronie klienta
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Dane timera
    duration INTEGER NOT NULL,  -- Czas w sekundach
    label TEXT NOT NULL,  -- Etykieta/opis timera
    enabled BOOLEAN DEFAULT FALSE,  -- Czy timer jest aktywny
    remaining INTEGER,  -- Pozostały czas (NULL jeśli nie uruchomiony)
    
    -- Opcje
    play_sound BOOLEAN DEFAULT TRUE,  -- Czy odtwarzać dźwięk
    show_popup BOOLEAN DEFAULT TRUE,  -- Czy pokazać popup
    repeat BOOLEAN DEFAULT FALSE,  -- Czy powtarzać timer
    custom_sound TEXT,  -- Ścieżka/URL do niestandardowego dźwięku
    
    -- Stan timera
    started_at TIMESTAMP WITH TIME ZONE,  -- Kiedy uruchomiono timer
    
    -- Synchronizacja local-first
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete
    synced_at TIMESTAMP WITH TIME ZONE,  -- Ostatnia synchronizacja
    version INTEGER DEFAULT 1,  -- Wersja dla conflict resolution
    
    -- Walidacja
    CONSTRAINT timers_duration_positive CHECK (duration > 0)
);

-- Indeksy dla optymalizacji zapytań
CREATE INDEX IF NOT EXISTS idx_timers_user_id ON s01_user_accounts.timers(user_id);
CREATE INDEX IF NOT EXISTS idx_timers_enabled ON s01_user_accounts.timers(enabled) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_timers_synced ON s01_user_accounts.timers(synced_at);
CREATE INDEX IF NOT EXISTS idx_timers_deleted ON s01_user_accounts.timers(deleted_at);


-- Tabela: alarm_sync_log
-- Log synchronizacji dla debugowania i conflict resolution
CREATE TABLE IF NOT EXISTS s01_user_accounts.alarm_sync_log (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,  -- 'alarm' lub 'timer'
    entity_id TEXT NOT NULL,  -- ID alarmu/timera
    action TEXT NOT NULL,  -- 'create', 'update', 'delete'
    data JSONB,  -- Dane przed/po zmianie
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    conflict_resolved BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT alarm_sync_entity_check CHECK (entity_type IN ('alarm', 'timer')),
    CONSTRAINT alarm_sync_action_check CHECK (action IN ('create', 'update', 'delete'))
);

-- Indeks dla logów
CREATE INDEX IF NOT EXISTS idx_alarm_sync_user ON s01_user_accounts.alarm_sync_log(user_id);
CREATE INDEX IF NOT EXISTS idx_alarm_sync_entity ON s01_user_accounts.alarm_sync_log(entity_id);


-- Trigger do automatycznej aktualizacji updated_at
CREATE OR REPLACE FUNCTION s01_user_accounts.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Dodaj trigger do alarms
DROP TRIGGER IF EXISTS update_alarms_updated_at ON s01_user_accounts.alarms;
CREATE TRIGGER update_alarms_updated_at
    BEFORE UPDATE ON s01_user_accounts.alarms
    FOR EACH ROW
    EXECUTE FUNCTION s01_user_accounts.update_updated_at_column();

-- Dodaj trigger do timers
DROP TRIGGER IF EXISTS update_timers_updated_at ON s01_user_accounts.timers;
CREATE TRIGGER update_timers_updated_at
    BEFORE UPDATE ON s01_user_accounts.timers
    FOR EACH ROW
    EXECUTE FUNCTION s01_user_accounts.update_updated_at_column();


-- ============================================================================
-- PRZYKŁADOWE ZAPYTANIA (QUERIES)
-- ============================================================================

-- Pobranie wszystkich aktywnych alarmów użytkownika
/*
SELECT * FROM s01_user_accounts.alarms
WHERE user_id = 'user_uuid'
  AND deleted_at IS NULL
ORDER BY time ASC;
*/

-- Pobranie alarmów wymagających synchronizacji
/*
SELECT * FROM s01_user_accounts.alarms
WHERE user_id = 'user_uuid'
  AND (synced_at IS NULL OR updated_at > synced_at)
  AND deleted_at IS NULL;
*/

-- Pobranie wszystkich aktywnych timerów użytkownika
/*
SELECT * FROM s01_user_accounts.timers
WHERE user_id = 'user_uuid'
  AND deleted_at IS NULL
ORDER BY created_at DESC;
*/

-- Soft delete alarmu
/*
UPDATE s01_user_accounts.alarms
SET deleted_at = NOW(), version = version + 1
WHERE id = 'alarm_uuid' AND user_id = 'user_uuid';
*/

-- Oznaczenie jako zsynchronizowane
/*
UPDATE s01_user_accounts.alarms
SET synced_at = NOW()
WHERE id = 'alarm_uuid' AND user_id = 'user_uuid';
*/

-- Sprawdzenie konfliktów (lokalna wersja > zdalna wersja)
/*
SELECT * FROM s01_user_accounts.alarms
WHERE id = 'alarm_uuid' 
  AND version > (SELECT version FROM remote_data);
*/
