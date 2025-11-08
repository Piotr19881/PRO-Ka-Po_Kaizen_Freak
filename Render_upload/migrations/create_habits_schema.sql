-- =============================================================================
-- Migration: Create s07_habits schema for Habit Tracker synchronization
-- Date: 2025-11-07
-- Version: 1.0
-- =============================================================================

-- 1. Utwórz schemat
CREATE SCHEMA IF NOT EXISTS s07_habits;

-- 2. Ustaw search_path (dla wygody)
SET search_path TO s07_habits, public;

-- =============================================================================
-- TABELA: habit_columns
-- Definicje kolumn nawyków
-- =============================================================================

CREATE TABLE IF NOT EXISTS s07_habits.habit_columns (
    -- Primary key
    id TEXT PRIMARY KEY,  -- UUID z klienta
    
    -- Foreign keys
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Core fields
    name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
    type TEXT NOT NULL CHECK (type IN ('checkbox', 'counter', 'duration', 'time', 'scale', 'text')),
    position INTEGER NOT NULL DEFAULT 0,
    scale_max INTEGER DEFAULT 10,  -- Dla typu 'scale'
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,  -- Soft delete
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1
    
    -- No unique constraints with WHERE clause in table definition
);

-- Indexes dla habit_columns
CREATE INDEX idx_habit_columns_user ON s07_habits.habit_columns(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_habit_columns_position ON s07_habits.habit_columns(user_id, position) WHERE deleted_at IS NULL;
CREATE INDEX idx_habit_columns_updated ON s07_habits.habit_columns(updated_at DESC);
CREATE INDEX idx_habit_columns_deleted ON s07_habits.habit_columns(deleted_at) WHERE deleted_at IS NOT NULL;

-- Unique constraint jako partial index
CREATE UNIQUE INDEX idx_habit_columns_unique_user_name ON s07_habits.habit_columns(user_id, name) WHERE deleted_at IS NULL;

-- Trigger dla updated_at
CREATE OR REPLACE FUNCTION s07_habits.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_habit_columns_updated_at
    BEFORE UPDATE ON s07_habits.habit_columns
    FOR EACH ROW
    EXECUTE FUNCTION s07_habits.update_updated_at_column();

-- =============================================================================
-- TABELA: habit_records
-- Wartości nawyków dla konkretnych dat
-- =============================================================================

CREATE TABLE IF NOT EXISTS s07_habits.habit_records (
    -- Primary key
    id TEXT PRIMARY KEY,  -- UUID z klienta
    
    -- Foreign keys
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    habit_id TEXT NOT NULL REFERENCES s07_habits.habit_columns(id) ON DELETE CASCADE,
    
    -- Core fields
    date DATE NOT NULL,  -- Data rekordu
    value TEXT,  -- Wartość (może być pusta)
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_habit_date UNIQUE (user_id, habit_id, date)
);

-- Indexes dla habit_records
CREATE INDEX idx_habit_records_user ON s07_habits.habit_records(user_id);
CREATE INDEX idx_habit_records_habit ON s07_habits.habit_records(habit_id);
CREATE INDEX idx_habit_records_date ON s07_habits.habit_records(user_id, date DESC);
-- CREATE INDEX idx_habit_records_month ON s07_habits.habit_records(user_id, date_trunc('month', date)); -- Commented out due to IMMUTABLE constraint
CREATE INDEX idx_habit_records_updated ON s07_habits.habit_records(updated_at DESC);

CREATE TRIGGER update_habit_records_updated_at
    BEFORE UPDATE ON s07_habits.habit_records
    FOR EACH ROW
    EXECUTE FUNCTION s07_habits.update_updated_at_column();

-- =============================================================================
-- UWAGA: habit_settings NIE są synchronizowane!
-- Wszystkie ustawienia UI (szerokości kolumn, preferencje) zapisywane tylko lokalnie w SQLite
-- =============================================================================

-- =============================================================================
-- PERMISSIONS
-- =============================================================================

-- Grant permissions dla użytkownika aplikacji (jeśli używasz innego usera)
-- GRANT USAGE ON SCHEMA s07_habits TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA s07_habits TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA s07_habits TO your_app_user;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Sprawdź utworzone tabele
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 's07_habits' 
ORDER BY table_name;

-- Powinno pokazać 2 tabele:
-- 1. habit_columns
-- 2. habit_records
-- (habit_settings = tylko lokalne, nie w PostgreSQL)

-- Sprawdź indexes
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 's07_habits' 
ORDER BY tablename, indexname;

-- Sprawdź triggers
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 's07_habits' 
ORDER BY event_object_table, trigger_name;

-- =============================================================================
-- EXAMPLE DATA (opcjonalne dla testów)
-- =============================================================================

-- Przykładowe kolumny nawyków (usunąć w produkcji)
/*
INSERT INTO s07_habits.habit_columns (id, user_id, name, type, position) VALUES
('test-habit-1', 'test-user-id', 'Ćwiczenia', 'checkbox', 0),
('test-habit-2', 'test-user-id', 'Czytanie (min)', 'duration', 1),
('test-habit-3', 'test-user-id', 'Nastrój', 'scale', 2);

-- Przykładowe rekordy (usunąć w produkcji)
INSERT INTO s07_habits.habit_records (id, user_id, habit_id, date, value) VALUES
('test-record-1', 'test-user-id', 'test-habit-1', '2025-11-07', '1'),
('test-record-2', 'test-user-id', 'test-habit-2', '2025-11-07', '30:00'),
('test-record-3', 'test-user-id', 'test-habit-3', '2025-11-07', '8');
*/