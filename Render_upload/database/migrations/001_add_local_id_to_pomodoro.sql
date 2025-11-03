-- =====================================================
-- MIGRACJA: Dodanie kolumny local_id do tabel Pomodoro
-- Data: 2025-11-02
-- Opis: Dodaje pole local_id do synchronizacji local-first
-- =====================================================

-- Dodaj local_id do session_topics
ALTER TABLE s05_pomodoro.session_topics 
ADD COLUMN IF NOT EXISTS local_id VARCHAR(255);

-- Utwórz indeks dla szybszego wyszukiwania
CREATE INDEX IF NOT EXISTS idx_session_topics_local_id 
ON s05_pomodoro.session_topics(local_id);

-- Dodaj unique constraint dla kombinacji user_id + local_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_topics_user_local 
ON s05_pomodoro.session_topics(user_id, local_id) 
WHERE deleted_at IS NULL;

-- Dodaj local_id do session_logs
ALTER TABLE s05_pomodoro.session_logs 
ADD COLUMN IF NOT EXISTS local_id VARCHAR(255);

-- Utwórz indeks dla szybszego wyszukiwania
CREATE INDEX IF NOT EXISTS idx_session_logs_local_id 
ON s05_pomodoro.session_logs(local_id);

-- Dodaj unique constraint dla kombinacji user_id + local_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_logs_user_local 
ON s05_pomodoro.session_logs(user_id, local_id) 
WHERE deleted_at IS NULL;

-- Wypełnij istniejące rekordy tymczasowymi local_id (jeśli są jakieś dane)
UPDATE s05_pomodoro.session_topics 
SET local_id = 'migrated_' || id::text 
WHERE local_id IS NULL;

UPDATE s05_pomodoro.session_logs 
SET local_id = 'migrated_' || id::text 
WHERE local_id IS NULL;

-- Ustaw NOT NULL constraint po wypełnieniu danych
ALTER TABLE s05_pomodoro.session_topics 
ALTER COLUMN local_id SET NOT NULL;

ALTER TABLE s05_pomodoro.session_logs 
ALTER COLUMN local_id SET NOT NULL;

-- Wyświetl potwierdzenie
DO $$
BEGIN
    RAISE NOTICE 'Migracja zakończona pomyślnie!';
    RAISE NOTICE 'Dodano kolumnę local_id do session_topics i session_logs';
END $$;
